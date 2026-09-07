"""The spectator display: one cave you can look into, with the machine's own map over it.

SPECTATOR-DISPLAY.md, slice 1. The main region holds the cave as it really is, in three
dimensions, with a director camera that holds the whole place when nothing is happening
and moves in on the beat when something is. The map the machine has built is the small
picture in the corner -- unchanged from the display the gate failed on, on its old
camera, given the inset's rectangle and otherwise untouched. The minimap in the opposite
corner is the one thing on screen that never changes meaning.

Truth is big by default because the gate failed on legibility and everything legible is
on the truth side: the filled cave, the eleven named rooms, the drawn rival, the
countdown clock, the tether with a number on it. The belief scene has no names in it by
construction -- the machine does not know what room it is in.

What this class may see: `MatchView`, which yields Beliefs, Policies and a frozen
`StageFrame`. There is no `Sim` here and no `World` reachable from anything it holds.

Camera: the director drives it. Slice 1 binds no mouse. R sends Recall.
"""
from __future__ import annotations

import math
import time

import numpy as np
from vispy import app, io, scene
from vispy.scene import visuals

from .. import tuning as T
from ..belief.belief import Belief
from ..match.match_view import MatchView
from ..match.stage_frame import StageFrame
from ..sound_character import SoundCharacter
from . import palette
from .director import Director
from .event_feed import EventFeed
from .minimap import Minimap
from .shapes import ring, to_segments, wedge
from .status_panel import StatusPanel
from .timeline import TimelineView
from .truth_panel import TruthPanel

FIX_ANIM_SECONDS: float = 0.7

FRIENDLY: dict[str, str] = {"DA": "deposit A", "DB": "deposit B",
                            "S": "the shaft", "HOME": "the shaft"}
STATUS_LABELS: tuple[str, ...] = ("CARGO", "IT THINKS IT KNOWS WHERE IT IS TO",
                                  "LAST POSITION FIX", "MAP IT HAS BUILT",
                                  "YOUR ONE COMMAND")
MAIN_TITLE: str = "THE CAVE     what is actually there"
INSET_TITLE: str = "ITS MAP     what it thinks is there"


class View:
    def __init__(self, match: MatchView, audio: object | None = None, show: bool = True,
                 size: tuple[int, int] = (T.CANVAS_W, T.CANVAS_H)) -> None:
        self.match: MatchView = match
        self.audio = audio
        self.b: Belief = match.beliefs["player"]
        self.size: tuple[int, int] = size
        w, h = size

        self.canvas = scene.SceneCanvas(title="BLINDSIDE", size=size,
                                        bgcolor=palette.VOID,
                                        keys="interactive", show=show)
        overlay = self.canvas.scene
        frame = match.stage()

        # ---- the three scenes. Order matters: the two overlays are drawn last, over
        # the main view, and `clip_children` keeps each one inside its own rectangle.
        self.truth_view = scene.ViewBox(parent=overlay, bgcolor=palette.VOID)
        self.truth_view.camera = scene.TurntableCamera(
            elevation=T.ELEVATION_DEFAULT_DEG, azimuth=0.0, fov=0, up="z")
        self.truth_view.camera.center = (100.0, 60.0, 0.0)
        self.truth_view.interactive = False       # the director drives it; slice 4 is the mouse

        # The belief scene is exactly what it was, on exactly the camera it had. A
        # layout change and nothing else -- the slice-3 rebuild is a separate look.
        self.view = scene.ViewBox(parent=overlay, bgcolor=palette.BACKGROUND)
        belief_camera = scene.TurntableCamera(elevation=58, azimuth=0, fov=0, up="z")
        belief_camera.center = (100, 60, 0)
        belief_camera.scale_factor = 150
        self.view.camera = belief_camera
        self.view.interactive = False

        self.minimap_view = scene.ViewBox(parent=overlay, bgcolor=palette.VOID)
        self.minimap_view.camera = scene.PanZoomCamera(aspect=1)
        self.minimap_view.camera.rect = (0, 0, frame.grid.shape[1], frame.grid.shape[0])
        self.minimap_view.interactive = False     # it pans on its own drag; switch it off

        self.truth: TruthPanel = TruthPanel(self.truth_view.scene, frame)
        self.minimap: Minimap = Minimap(self.minimap_view.scene, frame.grid)
        self.director: Director = Director(vertical_fraction=1.0)

        self._belief_visuals(self.view.scene)
        self._chrome(overlay, w, h)

        self.feed: EventFeed = EventFeed(self.b)
        self._header_cache: str = ""
        self._prev_xy: tuple[np.ndarray, np.ndarray] | None = None
        self._anim_from: tuple[np.ndarray, np.ndarray] | None = None
        self._anim_start: float = -1e9
        self._fix_easing: bool = False
        self._n_fixes_seen: int = 0
        self.revealed: bool = False
        self.reveal_visuals: list[object] = []
        self._wall_clock_zero: float | None = None
        self._last_t: float = 0.0
        self._main: tuple[float, float, float, float] = (0.0, 0.0, float(w), float(h))

        self.canvas.events.key_press.connect(self.on_key)
        self.canvas.events.resize.connect(self.on_resize)
        self._layout(float(w), float(h))
        # The frame loop runs on a Qt timer rather than vispy's app.Timer.
        #
        # A vispy Timer created here never fired even once, while a second Timer in
        # the same process fired normally -- so the window painted its chrome and then
        # sat there forever, which is what a black screen turned out to be. Driving it
        # from the canvas's draw event instead advanced exactly one frame, because an
        # update() requested from inside a draw is coalesced into the draw already in
        # progress. A Qt timer has neither problem and is what vispy is sitting on
        # anyway.
        self.live: bool = show
        self.timer: object | None = None

    # ---- construction -------------------------------------------------------------------
    def _belief_visuals(self, s: object) -> None:
        """Unchanged from the display the gate was run on."""
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
                  self.beacon_chain, self.beacons, self.places, self.agent,
                  self.intent_marker):
            v.set_gl_state("translucent", depth_test=False)

    def _chrome(self, overlay: object, w: float, h: float) -> None:
        """Words and grounds. Every `Rectangle` here is touched only in `_layout()`:
        setting any property on one regenerates its geometry and forces a synchronous
        repaint, and a *static* one costs nothing."""
        self.panel_header = self._panel(overlay, w / 2, T.HEADER_H / 2, w, T.HEADER_H)
        self.panel_rail = self._panel(overlay, w - T.RAIL_W / 2, h / 2, T.RAIL_W, h)
        self.panel_timeline = self._panel(overlay, w / 2, h - T.TIMELINE_H / 2,
                                          w, T.TIMELINE_H)

        self.title = visuals.Text("BLINDSIDE", parent=overlay, pos=(18, T.HEADER_H / 2),
                                  anchor_x="left", anchor_y="center", color=palette.TITLE,
                                  font_size=15, bold=True)
        self.subtitle = visuals.Text(
            "nobody is driving it", parent=overlay, pos=(196, T.HEADER_H / 2),
            anchor_x="left", anchor_y="center", color=palette.DIM, font_size=11)
        self.header_right = visuals.Text("", parent=overlay, pos=(w - 18, T.HEADER_H / 2),
                                         anchor_x="right", anchor_y="center",
                                         color=palette.BANNER, font_size=11, bold=True)
        self.main_title = visuals.Text(MAIN_TITLE, parent=overlay, anchor_x="left",
                                       anchor_y="center", color=palette.HUD,
                                       font_size=11, bold=True, pos=(T.MARGIN, 0))
        self.compass = visuals.Text("N", parent=overlay, anchor_x="right",
                                    anchor_y="center", color=palette.DIM,
                                    font_size=11, pos=(0, 0))
        self.inset_title = visuals.Text(INSET_TITLE, parent=overlay, anchor_x="left",
                                        anchor_y="bottom", color=palette.DIM,
                                        font_size=9, pos=(0, 0))
        self.status = StatusPanel(overlay, 0.0, 0.0, T.RAIL_W - 2 * T.MARGIN,
                                  STATUS_LABELS)
        self.timeline = TimelineView(overlay, T.MARGIN, h - T.TIMELINE_H + 6,
                                     w - 2 * T.MARGIN, T.TIMELINE_H - 12)

    # ---- layout ------------------------------------------------------------------------
    def _layout(self, w: float, h: float) -> None:
        """Everything positional is derived from the *live* canvas size.

        `show()` clamps the canvas to the screen and `render()` does not, so the live
        frame and the recorded frame are different sizes -- a layout tuned by eye in the
        window is not the layout in the mp4. The inset is a fraction of the main view
        and the minimap is one pixel per cell, so neither is ever hand-placed.
        """
        main_x, main_y = T.MARGIN, T.HEADER_H + T.TITLE_H
        main_w = max(w - 3 * T.MARGIN - T.RAIL_W, 200.0)
        main_h = max(h - T.HEADER_H - T.TITLE_H - T.TIMELINE_H, 150.0)
        self._main = (main_x, main_y, main_w, main_h)
        self.truth_view.pos = (main_x, main_y)
        self.truth_view.size = (main_w, main_h)

        inset_w = main_w * T.PIP_INSET_FRACTION
        inset_h = main_h * T.PIP_INSET_FRACTION
        inset_x = main_x + main_w - T.MARGIN - inset_w
        inset_y = main_y + T.MARGIN
        self.view.pos = (inset_x, inset_y)
        self.view.size = (inset_w, inset_h)

        mini_w = self.minimap.cols * T.MINIMAP_PX_PER_CELL
        mini_h = self.minimap.rows * T.MINIMAP_PX_PER_CELL
        mini_x = main_x + T.MARGIN
        mini_y = main_y + main_h - T.MARGIN - mini_h
        self.minimap_view.pos = (mini_x, mini_y)
        self.minimap_view.size = (mini_w, mini_h)
        _assert_overlays_clear(main_w, main_h,
                               (inset_x - main_x, inset_y - main_y, inset_w, inset_h),
                               (mini_x - main_x, mini_y - main_y, mini_w, mini_h))

        # The director frames in cells across the rectangle, so it needs to know how
        # much of that width fits in the height: the aspect, undone by the tilt.
        elevation = math.radians(self.truth_view.camera.elevation)
        self.director.vertical_fraction = (main_h / main_w) / max(math.sin(elevation), 1e-3)

        self.panel_header.center = (w / 2, T.HEADER_H / 2)
        self.panel_header.width = w
        self.panel_rail.center = (w - T.RAIL_W / 2, h / 2)
        self.panel_rail.height = h
        self.panel_timeline.center = (w / 2, h - T.TIMELINE_H / 2)
        self.panel_timeline.width = w
        self.header_right.pos = (w - T.RAIL_W - 2 * T.MARGIN, T.HEADER_H / 2)
        self.subtitle.visible = w > 760
        self.main_title.pos = (main_x, T.HEADER_H + T.TITLE_H / 2)
        self.compass.pos = (main_x + main_w, T.HEADER_H + T.TITLE_H / 2)
        self.inset_title.pos = (inset_x, inset_y - 4)
        self.status.move(w - T.RAIL_W + T.MARGIN, T.HEADER_H + T.MARGIN + 10)
        self.timeline.move(T.MARGIN, h - T.TIMELINE_H + 20, max(w - 2 * T.MARGIN, 80))

    def on_resize(self, ev: object) -> None:
        w, h = self.canvas.size
        self._layout(float(w), float(h))

    # ---- chrome helpers ---------------------------------------------------------------
    @staticmethod
    def _panel(parent: object, cx: float, cy: float, w: float, h: float) -> object:
        return visuals.Rectangle(center=(cx, cy), width=w, height=h,
                                 color=palette.PANEL, border_color=palette.PANEL_EDGE,
                                 border_width=1, parent=parent)

    # ---- input ------------------------------------------------------------------------
    def on_key(self, ev: object) -> None:
        key = getattr(ev, "key", None)
        if key is not None and key.name.lower() == "r":
            if self.match.recall() and self.audio is not None:
                self.audio.recall_sent()      # type: ignore[attr-defined]

    # ---- frame ------------------------------------------------------------------------
    def start(self) -> None:
        """Kept for symmetry; the frame timer is owned by the entry point.

        Every attempt to own the timer inside this class failed, and failed
        inconsistently -- fired once, then not at all. A timer created by the caller
        and held in a local that outlives app.run() works every time.
        """
        return

    def advance(self) -> None:
        if self._wall_clock_zero is None:
            self._wall_clock_zero = time.perf_counter()
        self.match.advance_to(time.perf_counter() - self._wall_clock_zero, max_steps=8)
        self.draw()
        if self.live:
            self.canvas.update()

    def draw(self) -> None:
        b, t = self.b, self.match.t
        frame = self.match.stage()
        self.feed.update(t)
        self._draw_cloud(b, t)
        self._draw_places(b)
        self._draw_agent(b)
        self._draw_intent(b)
        self._draw_believed(b)
        self._draw_contacts(b, t)
        self._draw_fronts(b, t)
        self._draw_fix(b, t)
        self._draw_truth(frame, b)
        self._draw_panels(b, t)
        self.timeline.update(self.feed, t)
        if self.audio is not None:
            self.audio.update(b, t, self.view.camera.azimuth)   # type: ignore[attr-defined]
        if self.match.over and not self.revealed:
            self._reveal()

    # ---- the cave -------------------------------------------------------------------------
    def _draw_truth(self, frame: StageFrame, b: Belief) -> None:
        """The camera runs on *sim* time, not on the wall clock, so a recorded match
        and a live one move the camera identically."""
        dt = max(0.0, frame.t - self._last_t)
        self._last_t = frame.t
        self.director.update(frame, dt, self._fix_easing)

        _, _, main_w, main_h = self._main
        camera = self.truth_view.camera
        camera.center = (self.director.cx, self.director.cy, 0.0)
        camera.scale_factor = _scale_for(self.director.cells, main_w, main_h)
        elevation = math.radians(camera.elevation)
        fx = self.director.cells
        fy = fx * (main_h / main_w)
        self.truth.update(frame, (b.x, b.y, b.theta),
                          (self.director.cx, self.director.cy, fx, fy,
                           math.sin(elevation), math.cos(elevation)))
        self.minimap.update(frame, self.director.cx, self.director.cy,
                            self.director.cells, self.director.vertical_fraction)

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
        self._fix_easing = self._anim_from is not None and 0.0 <= progress < 1.0
        if self._fix_easing and self._anim_from is not None:
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
        # Lidar is precise and dense; drawn at sonar size it turns into a blob. Small
        # points let a lidar map read as a wall line, and the ghosting still shows.
        lidar = b.cloud.source[:n] == 3
        size[lidar] = 2.2
        alpha[lidar] = 0.55 + 0.35 * q[lidar]
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
        policy = self.match.policies["player"]
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
        for t_scan in b.own_scans[-3:]:
            age = t - t_scan
            if 0.0 <= age < 0.45:
                sweep = ring(b.x, b.y, T.LIDAR_RANGE, n=96, z=0.12)
                segments += list(to_segments(sweep))
                colours += [(0.55, 0.88, 1.0, 0.35 * (1 - age / 0.45))] * (2 * 96 - 2)
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

    # ---- the rail ---------------------------------------------------------------------------
    def _draw_panels(self, b: Belief, t: float) -> None:
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
            f"within {b.sigma_pos():.0f} cell" + ("" if round(b.sigma_pos()) == 1 else "s"),
            fix_text,
            (f"{(b.cloud.n // 50) * 50} points, {len(b.own_scans)} sweeps" if b.sensor == "lidar"
             else f"{(b.cloud.n // 50) * 50} points, {len(b.own_pings)} pings"),
            "spent" if self.match.recall_used else "ready - press R",
        ), (
            None,
            palette.BANNER if b.sigma_pos() > 12 else palette.TITLE,
            palette.BANNER if surprised else palette.TITLE,
            None,
            palette.DIM if self.match.recall_used else palette.TREE_LIVE,
        ))

        result = self.match.result
        if self.match.over and result is not None:
            header = f"MATCH OVER - {result.player_outcome}, cargo {result.cargo}"
        elif t >= T.EXTRACT_WINDOW_OPENS:
            header = "EXTRACTION WINDOW OPEN"
        else:
            left = T.EXTRACT_WINDOW_OPENS - t
            header = f"extraction opens in {int(left) // 60}:{int(left) % 60:02d}"
        if header != self._header_cache:
            self._header_cache = header
            self.header_right.text = header

    @staticmethod
    def _place_name(label: str) -> str:
        if label in FRIENDLY:
            return FRIENDLY[label]
        return "its own beacon" if label.startswith("player_") else f"survey point {label}"

    # ---- after the end ------------------------------------------------------------------------
    @staticmethod
    def _over_the_cave(visual: object) -> object:
        """Anything drawn in the inset sits over the cave mesh's depth, and vispy's
        "translucent" preset leaves depth testing on -- so an overlay that does not
        switch it off is discarded without a word."""
        visual.set_gl_state("translucent", depth_test=False)   # type: ignore[attr-defined]
        return visual

    def _reveal(self) -> None:
        """The true outline over the map the machine built, in the belief scene.

        Slice 9 retargets this as a scripted swap so it lands in the main rectangle;
        until then it is what it was, in the picture it was always drawn in.
        """
        self.revealed = True
        r = self.match.reveal()
        s = self.view.scene

        walls = np.column_stack([r.walls, np.full(len(r.walls), -0.1)])
        wall_vis = self._over_the_cave(visuals.Markers(parent=s))
        wall_vis.set_data(walls, face_color=palette.TRUTH_WALL, size=2.5, edge_width=0)
        self.reveal_visuals.append(wall_vis)

        if len(r.flooded):
            flooded = np.column_stack([r.flooded, np.full(len(r.flooded), -0.1)])
            flood_vis = self._over_the_cave(visuals.Markers(parent=s))
            flood_vis.set_data(flooded, face_color=palette.TRUTH_FLOOD, size=2, edge_width=0)
            self.reveal_visuals.append(flood_vis)

        for name, colour, width in (("player", palette.TRUTH_TRAIL_PLAYER, 2),
                                    ("rival", palette.TRUTH_TRAIL_RIVAL, 1.5)):
            path = r.truth_trail.get(name)
            if path:
                self.reveal_visuals.append(self._over_the_cave(visuals.Line(
                    parent=s, pos=np.array([(x, y, 0.3) for x, y, _ in path]),
                    color=colour, width=width)))

        ax, ay, ar = r.ancient
        self.reveal_visuals.append(self._over_the_cave(
            visuals.Line(parent=s, pos=ring(ax, ay, ar, z=0.3),
                         color=(*palette.SIGNATURE, 0.9), width=2)))
        ends = np.array([[x, y, 0.35] for (x, y, _, _) in r.agents.values()])
        end_vis = self._over_the_cave(visuals.Markers(parent=s))
        end_vis.set_data(ends, face_color=palette.TRUTH_TRAIL_PLAYER, size=12, symbol="x")
        self.reveal_visuals.append(end_vis)

        own = np.array([[x, y, 0.35] for (x, y, owner) in r.beacons.values() if owner == "player"])
        if len(own):
            beacon_vis = self._over_the_cave(visuals.Markers(parent=s))
            beacon_vis.set_data(own, face_color=palette.TRUTH_BEACON, size=7, symbol="diamond")
            self.reveal_visuals.append(beacon_vis)

        for dx, dy in r.deposits.values():
            self.reveal_visuals.append(self._over_the_cave(
                visuals.Line(parent=s, pos=ring(dx, dy, 3, n=24, z=0.3),
                             color=palette.TRUTH_DEPOSIT, width=2)))

    # ---- offscreen -----------------------------------------------------------------------------
    def snapshot(self, path: str) -> None:
        self.draw()
        io.write_png(path, self.canvas.render())


# ---- framing ------------------------------------------------------------------------------------
def _scale_for(cells: float, w: float, h: float) -> float:
    """`scale_factor` that puts `cells` across the rectangle's width.

    vispy's orthographic turntable stretches the *longer* axis by the aspect, so the
    scale factor is the short axis. Framing is stated in cells rather than in
    `scale_factor` three times over: scale_factor means different things at different
    aspect ratios, the live and recorded canvases are different sizes, and a scene that
    changes rectangle has to keep its framing.
    """
    return cells * h / w if w > h else cells


def _assert_overlays_clear(main_w: float, main_h: float,
                           inset: tuple[float, float, float, float],
                           minimap: tuple[float, float, float, float]) -> None:
    """The overlays must not cover the beat.

    At CLOSE framing the subject is centred, so the machinery's 9-cell ring reaches a
    known radius from the centre of the main view. This asserts the clearance rather
    than the fraction, so a future `PIP_INSET_FRACTION` that covers the machinery fails
    loudly at start-up instead of quietly eating the target beat.
    """
    px_per_cell = main_w / T.CAMERA_CLOSE_CELLS
    reach = T.ANCIENT_RADIUS * px_per_cell
    cx, cy = main_w / 2.0, main_h / 2.0
    for name, (x, y, w, h) in (("the inset", inset), ("the minimap", minimap)):
        near_x = min(max(cx, x), x + w)
        near_y = min(max(cy, y), y + h)
        clearance = math.hypot(near_x - cx, near_y - cy) - reach
        assert clearance > 0.0, (
            f"{name} covers the CLOSE hazard ring by {-clearance:.0f} px: "
            "lower PIP_INSET_FRACTION or widen RAIL_W")
