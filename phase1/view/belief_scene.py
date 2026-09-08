"""The machine's own map: the belief scene, drawn the same in every window.

Moved out of `view.py` verbatim so that the teach window (`teach_view.py`) can draw
exactly the picture the spectator display's inset draws -- points where the agent
believed it was when it sensed them, the trail, the chain, the ellipse, the intent
line, every wedge it heard -- without a second copy of any of it. **What is drawn
here is Belief and nothing else.** The one thing handed in from outside Belief is the
policy's current waypoint, for the intent line, which is the policy's own belief
about where it is going.
"""
from __future__ import annotations

import math

import numpy as np
from vispy.scene import visuals

from .. import tuning as T
from ..belief.belief import Belief
from ..policy.waypoint import Waypoint
from ..sound_character import SoundCharacter
from . import palette
from .shapes import ring, to_segments, wedge

FIX_ANIM_SECONDS: float = 0.7


class BeliefScene:
    """Every visual of the believed map, in one scene, and the state the fix ease keeps."""

    def __init__(self, parent: object, belief: Belief) -> None:
        self.b: Belief = belief
        self._prev_xy: tuple[np.ndarray, np.ndarray] | None = None
        self._anim_from: tuple[np.ndarray, np.ndarray] | None = None
        self._anim_start: float = -1e9
        self._fix_easing: bool = False
        self._n_fixes_seen: int = 0
        self._build(parent)

    @property
    def fix_easing(self) -> bool:
        """A fix is being eased across the map right now; the director holds for it."""
        return self._fix_easing

    def draw(self, t: float, target: Waypoint | None) -> None:
        b = self.b
        self._draw_cloud(b, t)
        self._draw_places(b)
        self._draw_agent(b)
        self._draw_intent(b, target)
        self._draw_believed(b)
        self._draw_contacts(b, t)
        self._draw_fronts(b, t)
        self._draw_fix(b, t)

    # ---- construction -------------------------------------------------------------------
    def _build(self, s: object) -> None:
        """Unchanged from the display the gate was run on."""
        self.cloud = visuals.Markers(parent=s)
        self.cloud.set_gl_state("translucent", depth_test=False)
        self.trail = visuals.Line(parent=s, color=(*palette.COOL_DIM, 0.30), width=1)
        self.beacon_chain = visuals.Line(parent=s, color=(*palette.COOL_DIM, 0.30), width=1)
        self.beacons = visuals.Markers(parent=s)
        self.places = visuals.Markers(parent=s)
        self.ellipse = visuals.Line(parent=s, color=(*palette.GHOST, 0.55), width=1.5)
        self.agent = visuals.Markers(parent=s)
        self.heading = visuals.Line(parent=s, color=(*palette.GHOST, 1.0), width=2)
        self.contacts = visuals.Line(parent=s, connect="segments", width=1.5)
        self.signature = visuals.Line(parent=s, connect="segments", width=2)
        self.fronts = visuals.Line(parent=s, connect="segments", width=1.2)
        self.fix_flash = visuals.Line(parent=s, connect="segments", width=2)
        self.intent = visuals.Line(parent=s, color=(*palette.GHOST, 0.40), width=1.5)
        self.intent_marker = visuals.Markers(parent=s)
        self.believed = visuals.Line(parent=s, connect="segments", width=1.5)
        for v in (self.trail, self.ellipse, self.heading, self.contacts, self.signature,
                  self.fronts, self.fix_flash, self.intent, self.believed,
                  self.beacon_chain, self.beacons, self.places, self.agent,
                  self.intent_marker):
            v.set_gl_state("translucent", depth_test=False)


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
        # Two classes and no third. The colour lerp, the alpha ramp, the size ramp and
        # three source overrides used to be four channels doing one job, and that is most
        # of why the map read as noise: confidence is alpha and size, and colour says only
        # whether the machine pinged this ground or merely walked over it.
        rgb = np.repeat(palette.POINT_SENSED[None, :], n, axis=0)
        alpha = 0.35 + 0.50 * q
        size = 2.4 + 3.0 * q
        rgb[walked] = palette.POINT_WALKED
        alpha[walked] = 0.20
        size[walked] = 1.6
        # Lidar is precise and dense; drawn at sonar size it turns into a blob. Small
        # points let a lidar map read as a wall line, and the ghosting still shows.
        lidar = b.cloud.source[:n] == 3
        size[lidar] = 1.8
        alpha[lidar] = 0.35 + 0.50 * q[lidar]
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
                                  face_color=(*palette.GHOST, 0.95), size=8,
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
            # Prior intel, not something it sensed: the objective is CARGO green wherever
            # it appears, in either picture, and the shaft is not its own colour.
            colours.append((*palette.CARGO, 0.85))
        if marks:
            self.places.set_data(np.array(marks), face_color=np.array(colours),
                                 size=14, symbol="ring", edge_width=0)
            self.places.visible = True


    def _draw_agent(self, b: Belief) -> None:
        self.agent.set_data(np.array([[b.x, b.y, 0.2]]), face_color=(*palette.GHOST, 1.0),
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


    def _draw_intent(self, b: Belief, wp: Waypoint | None) -> None:
        if wp is None:
            self.intent.visible = False
            self.intent_marker.visible = False
            return
        self.intent.set_data(np.array([[b.x, b.y, 0.18], [wp.x, wp.y, 0.18]]))
        self.intent_marker.set_data(np.array([[wp.x, wp.y, 0.18]]),
                                    face_color=(*palette.GHOST, 0.40), size=14,
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
        # Demoted from the brightest rings on screen to ambient, and kept: with the truth
        # scene in the other slot, the gap between where it thinks the machinery is and
        # where it is becomes a readable joke. Magenta is the machinery in every picture;
        # the rival is ember in every picture; a belief about one is the same hue, hollow.
        for tracker, colour in ((b.hazard_track, (*palette.HAZARD, 0.34)),
                                (b.rival_track, (*palette.EMBER, 0.34))):
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
            rgb = palette.CONTACT.get(c.character, palette.GHOST)
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
                                    color=(*palette.HAZARD, 0.30 + 0.6 * pulse * strength))
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
                colours += [(*palette.GHOST, 0.55 * (1 - age / T.WAVEFRONT_LIFE_S))] * (2 * 96 - 2)
        for t_scan in b.own_scans[-3:]:
            age = t - t_scan
            if 0.0 <= age < 0.45:
                sweep = ring(b.x, b.y, T.LIDAR_RANGE, n=96, z=0.12)
                segments += list(to_segments(sweep))
                colours += [(*palette.GHOST, 0.35 * (1 - age / 0.45))] * (2 * 96 - 2)
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
            colours += [(*palette.LIE, alpha)] * 2
            circle = ring(record.post_x, record.post_y, 1.5 + age * 4, n=32, z=0.2)
            segments += list(to_segments(circle))
            colours += [(*palette.LIE, alpha * 0.6)] * (2 * 32 - 2)
        if segments:
            self.fix_flash.set_data(np.array(segments), color=np.array(colours))
            self.fix_flash.visible = True
        else:
            self.fix_flash.visible = False

