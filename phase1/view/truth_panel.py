"""The cave as it really is, with the machine in it. SPECTATOR-DISPLAY.md section 6.4.

Consumes a `StageFrame` and the player's believed pose. It cannot import `truth` and it
cannot name `.world`; `match/invariant.py` rules 3 and 4 prove it. Everything real in
here arrived through the one-way channel in section 4, and the believed pose arrived
from `Belief`, which the renderer has always been allowed to read.

Slice 1 draws eight of the thirteen marks: the cave, the floor, the eleven names, both
machines to scale, both comets, the ghost, the tether, the machinery and its countdown,
and the deposits at their true radius. Beacons, sound rings, the spoof's dashed line
and the believed-machinery disc are later slices.

Every overlay is `translucent, depth_test=False` and ordered after the mesh, so the
subject is never lost behind rock; the tether and the chamber names are additionally
lifted above the wall height, which is the same result and is stable under orbit.
"""
from __future__ import annotations

import math

import numpy as np
from vispy.scene import visuals

from .. import tuning as T
from ..match.stage_frame import StageFrame
from . import palette
from .cave_mesh import CaveMesh
from .chamber_names import CHAMBER_LABELS
from .glyph import machine
from .shapes import ring, to_segments

# The camera, as the six numbers the off-frame stub needs: centre, the ortho half
# extents in scene units, and the elevation's sine and cosine. Slice 1 has no manual
# camera control, so azimuth is fixed at 0 and screen-right is world +x.
Camera = tuple[float, float, float, float, float, float]

HEAD_TURN_DEG_S: float = 34.0        # a still machine that is still looking is not dead
FLOOR_Z: float = 0.18                # clear of the floor image, under everything else
LABEL_Z: float = T.CAVE_WALL_HEIGHT_CELLS + 0.5
COUNTDOWN_Z: float = 2.0             # low: at LABEL_Z the lift pushed it out of frame
STUB_MARGIN: float = 0.90            # of the half-frame, so the arrow is inside the edge


class TruthPanel:
    def __init__(self, parent: object, frame: StageFrame) -> None:
        self.cave: CaveMesh = CaveMesh(parent, frame.grid,
                                       (frame.player.x, frame.player.y))

        self.names = visuals.Text(
            [name for name, _, _ in CHAMBER_LABELS],
            pos=np.array([[x, y, LABEL_Z] for _, x, y in CHAMBER_LABELS]),
            parent=parent, color=(*palette.WARM_DIM, 0.85), font_size=11,
            anchor_x="center", anchor_y="center")

        self.deposits = visuals.Line(parent=parent, connect="segments", width=1.5,
                                     color=(*palette.CARGO, 0.35))
        self.comet_player = visuals.Line(parent=parent, width=2.5)
        self.comet_rival = visuals.Line(parent=parent, width=2.0)
        self.hazard = visuals.Line(parent=parent, connect="segments", width=2.0)
        self.machines = visuals.Line(parent=parent, connect="segments", width=2.0)
        self.tether = visuals.Line(parent=parent, connect="segments", width=2.0)
        self.tether_label = visuals.Text("", parent=parent, pos=(0.0, 0.0, T.TETHER_Z_CELLS),
                                         color=(*palette.LIE, 0.95), font_size=15,
                                         bold=True, anchor_x="center", anchor_y="bottom")
        self.hazard_label = visuals.Text("", parent=parent, pos=(0.0, 0.0, COUNTDOWN_Z),
                                         color=(*palette.HAZARD, 0.95), font_size=11,
                                         bold=True, anchor_x="center", anchor_y="center")

        overlays = (self.names, self.deposits, self.comet_player, self.comet_rival,
                    self.hazard, self.machines, self.tether, self.tether_label,
                    self.hazard_label)
        for index, visual in enumerate(overlays):
            visual.set_gl_state("translucent", depth_test=False)
            visual.order = index + 1

        self._deposit_rings(frame)
        self._tether_rgb: tuple[float, float, float] = palette.LIE
        self._tether_text: str = ""
        self._hazard_text: str = ""

    # ---- built once ---------------------------------------------------------------------
    def _deposit_rings(self, frame: StageFrame) -> None:
        """At their **true** 12-cell radius. The reveal has been drawing 3, a lie by a
        factor of four, and it is why the ending reads as nothing: at 6:30 the machine
        is standing inside deposit B and the display has never said so."""
        segments: list[np.ndarray] = []
        for deposit in frame.deposits:
            segments += list(to_segments(ring(deposit.x, deposit.y, deposit.radius,
                                              n=64, z=FLOOR_Z)))
        self.deposits.set_data(np.array(segments)) if segments else None
        _show(self.deposits, bool(segments))

    # ---- one frame ------------------------------------------------------------------------
    def update(self, frame: StageFrame, believed: tuple[float, float, float],
               camera: Camera, in_main_slot: bool = True) -> None:
        self._comet(self.comet_player, frame.trail_player, frame.t, palette.BONE)
        self._comet(self.comet_rival, frame.trail_rival, frame.t, palette.EMBER)
        self._machines(frame, believed)
        self._machinery(frame, in_main_slot)
        self._tether(frame, believed, camera, in_main_slot)
        # Text inside a 3D scene takes font_size in points, so it does not shrink with
        # its ViewBox: eleven 11 pt names in a 300 px inset would cover the picture.
        # Toggling `visible` is a boolean and costs no atlas rebuild.
        _show(self.names, in_main_slot)

    # ---- marks 5 and 8: the comets ----------------------------------------------------------
    @staticmethod
    def _comet(visual: object, trail: np.ndarray, t: float, rgb: tuple[float, float, float]) -> None:
        """The last twenty seconds of where it has been, fading to nothing behind it.

        The machines move at 1.1 and 1.4 cells/s, which at whole-cave framing is six to
        eight pixels a second -- at or below the threshold where the eye registers
        movement at all. A moving gradient reads as motion even when the head does not.
        """
        recent = trail[trail[:, 2] >= t - T.COMET_SECONDS] if len(trail) else trail
        if len(recent) < 2:
            _show(visual, False)
            return
        age = (t - recent[:, 2]) / T.COMET_SECONDS
        colours = np.empty((len(recent), 4), dtype=np.float32)
        colours[:, :3] = rgb
        colours[:, 3] = np.clip(0.85 * (1.0 - age), 0.0, 1.0)
        points = np.column_stack([recent[:, 0], recent[:, 1],
                                  np.full(len(recent), FLOOR_Z * 0.6)])
        visual.set_data(points, color=colours)          # type: ignore[attr-defined]
        _show(visual, True)

    # ---- marks 4, 6, 8, 13: the machines, the ghost, the wreck ---------------------------------
    def _machines(self, frame: StageFrame, believed: tuple[float, float, float]) -> None:
        head = math.radians(frame.t * HEAD_TURN_DEG_S) % (2.0 * math.pi)
        bx, by, btheta = believed
        drawn: list[tuple[list[tuple[float, float, float, float]], tuple[float, float, float], float]] = [
            (machine(frame.player.x, frame.player.y, frame.player.heading,
                     T.GLYPH_LENGTH_CELLS, filled=True, alive=frame.player.alive,
                     cargo=frame.player.cargo, head=head),
             palette.KILL if not frame.player.alive else palette.BONE, 1.0),
            (machine(frame.rival.x, frame.rival.y, frame.rival.heading,
                     T.GLYPH_LENGTH_CELLS, filled=True, alive=frame.rival.alive,
                     cargo=frame.rival.cargo, head=-head),
             palette.KILL if not frame.rival.alive else palette.EMBER, 1.0),
            # Hollow, identical geometry, at the pose it believes it holds. Solid is the
            # thing; hollow is a belief about the thing.
            (machine(bx, by, btheta, T.GLYPH_LENGTH_CELLS, filled=False),
             palette.GHOST, 0.65),
        ]
        points: list[list[float]] = []
        colours: list[tuple[float, float, float, float]] = []
        for segments, rgb, alpha in drawn:
            for ax, ay, bxx, byy in segments:
                points += [[ax, ay, FLOOR_Z], [bxx, byy, FLOOR_Z]]
                colours += [(*rgb, alpha)] * 2
        self.machines.set_data(np.array(points, dtype=np.float32),
                               color=np.array(colours, dtype=np.float32))

    # ---- mark 9: the machinery -----------------------------------------------------------------
    def _machinery(self, frame: StageFrame, in_main_slot: bool) -> None:
        """Quiet, then a nine-second warning that fills the ring clockwise, then four
        lethal seconds. The seventy-five-second cycle is already in the sim, it is
        perfectly regular, and it has never been drawn."""
        a = frame.ancient
        until = a.seconds_until_lethal
        warning = a.signature_strength > 0.0 and not a.is_lethal
        points: list[list[float]] = []
        colours: list[tuple[float, float, float, float]] = []

        if a.is_lethal:
            # three flashes at 6 Hz, and the disc floods
            flash = 0.55 + 0.45 * math.sin(frame.t * 6.0 * 2.0 * math.pi)
            rgb, alpha, width = palette.KILL, 0.35 + 0.5 * flash, 4.0
            for k in range(28):
                angle = 2.0 * math.pi * k / 28.0
                points += [[a.x, a.y, FLOOR_Z], [a.x + math.cos(angle) * a.radius,
                                                 a.y + math.sin(angle) * a.radius, FLOOR_Z]]
                colours += [(*rgb, alpha * 0.55)] * 2
        elif warning:
            rgb, alpha, width = palette.HAZARD, 0.95, 3.0
        else:
            breathe = 0.5 + 0.5 * math.sin(frame.t * 0.1 * 2.0 * math.pi)
            rgb, alpha, width = palette.HAZARD, 0.08 + 0.06 * breathe, 1.5

        # The floor ring, filling clockwise from twelve o'clock across the nine-second
        # warning. A clock is the one countdown a stranger reads without being taught.
        steps = 72
        filled = 0.0 if not warning else 1.0 - min(max(until / T.ANCIENT_WARNING_S, 0.0), 1.0)
        circle = ring(a.x, a.y, a.radius, n=steps + 1,
                      a0=math.pi / 2.0, a1=math.pi / 2.0 - 2.0 * math.pi, z=FLOOR_Z)
        for k in range(steps):
            fraction = k / steps
            lit = warning and fraction <= filled
            edge = alpha if (a.is_lethal or not warning) else (0.95 if lit else 0.20)
            points += [list(circle[k]), list(circle[k + 1])]
            colours += [(*rgb, edge)] * 2

        # a faint cylinder to the cave's wall height, so the hazard reads as a volume
        # and is visible over a rock rim from any azimuth
        top = T.CAVE_WALL_HEIGHT_CELLS
        wall = 0.09 + 0.10 * a.signature_strength      # faint: a volume, not a barrel
        for k in range(0, steps, 9):
            points += [list(circle[k]), [circle[k][0], circle[k][1], top]]
            colours += [(*rgb, wall)] * 2
        for k in range(steps):
            points += [[circle[k][0], circle[k][1], top], [circle[k + 1][0], circle[k + 1][1], top]]
            colours += [(*rgb, wall)] * 2

        self.hazard.set_data(np.array(points, dtype=np.float32),
                             color=np.array(colours, dtype=np.float32), width=width)

        show = in_main_slot and until <= T.HAZARD_COUNTDOWN_FROM_S and not a.is_lethal
        text = f"LETHAL IN 0:{int(math.ceil(until)):02d}" if show else (
            "LETHAL NOW" if (in_main_slot and a.is_lethal) else "")
        if text != self._hazard_text:                    # gated on the integer second
            self._hazard_text = text
            self.hazard_label.text = text
        # Above the ring rather than beside it -- a machine can stand anywhere on the
        # rim and the one frame this label matters in has two of them on it -- and low,
        # because a label lifted to the wall height is lifted out of a CLOSE frame.
        self.hazard_label.pos = (a.x, a.y + a.radius + 1.2, COUNTDOWN_Z)
        _show(self.hazard_label, bool(text))

    # ---- mark 7: the tether ----------------------------------------------------------------------
    def _tether(self, frame: StageFrame, believed: tuple[float, float, float],
                camera: Camera, in_main_slot: bool) -> None:
        """A rope slung above the rock, from the machine to where it thinks it is.

        The only place the gap is drawn as one object rather than as a comparison the
        viewer has to make. It is above the rock because the believed pose is routinely
        on the far side of solid stone from the true one -- that is the whole point of
        it -- and a primary mark the ambient layer occludes is not primary.
        """
        px, py = frame.player.x, frame.player.y
        gx, gy, _ = believed
        gap = math.hypot(gx - px, gy - py)
        z = T.TETHER_Z_CELLS

        if gap < T.TETHER_MIN_CELLS:
            rgb, width, alpha = palette.COOL_DIM, 1.0, 0.7
        elif gap < T.TETHER_HOT_CELLS:
            rgb, width, alpha = palette.BONE, 2.0, 0.9
        elif gap < T.TETHER_ALARM_CELLS:
            rgb, width, alpha = palette.LIE, 3.0, 0.95
        else:
            # Deliberately still LIE, not KILL. The tether escalates by weight, never into
            # red: red means lethal and nothing else. A verifier watching the 5:43 beat read
            # the red tether as the danger and the red kill disc as scenery -- two meanings
            # sharing one colour, next to each other, at the loudest moment in the match.
            rgb, width, alpha = palette.LIE, 4.5, 1.0

        end_x, end_y, clipped = _clip_to_frame(px, py, gx, gy, z, camera)
        points: list[list[float]] = [[px, py, FLOOR_Z], [px, py, z],
                                     [px, py, z], [end_x, end_y, z]]
        if clipped:
            # Not a degraded case: an arrow going off the edge of the world says "it
            # thinks it is somewhere else entirely" more directly than a thin line to a
            # distant dot ever did.
            angle = math.atan2(end_y - py, end_x - px)
            for sign in (1.1, -1.1):
                points += [[end_x, end_y, z],
                           [end_x - math.cos(angle) * 1.5 - math.sin(angle) * sign,
                            end_y - math.sin(angle) * 1.5 + math.cos(angle) * sign, z]]
        else:
            points += [[end_x, end_y, z], [end_x, end_y, FLOOR_Z]]
        self.tether.set_data(np.array(points, dtype=np.float32),
                             color=(*rgb, alpha), width=width)

        show = in_main_slot and gap >= T.TETHER_MIN_CELLS
        arrow = "-> " if clipped else ""
        text = f"{arrow}{gap:.0f} cells" if show else ""
        if text != self._tether_text:                    # gated on the integer, ~1 Hz
            self._tether_text = text
            self.tether_label.text = text
        if clipped:
            # Beside the arrowhead, square to the rope. Along it would put the label on
            # the machine: the rope leaves the machine one cell above the rock, so on
            # screen it starts well above the glyph and crosses back over it whenever
            # the believed pose is downscreen -- which at CLOSE framing is most of the
            # match.
            back = math.atan2(end_y - py, end_x - px)
            self.tether_label.pos = (end_x + math.sin(back) * 2.6,
                                     end_y - math.cos(back) * 2.6, z + 0.8)
        else:
            self.tether_label.pos = ((px + end_x) / 2.0, (py + end_y) / 2.0, z + 0.8)
        if rgb != self._tether_rgb:
            self._tether_rgb = rgb
            self.tether_label.color = (*rgb, 0.95)
        _show(self.tether_label, bool(text))


def _show(visual: object, wanted: bool) -> None:
    """`Node.visible` always calls `update()`, whether or not the value changed."""
    if visual.visible is not wanted:                    # type: ignore[attr-defined]
        visual.visible = wanted                         # type: ignore[attr-defined]


def _clip_to_frame(px: float, py: float, gx: float, gy: float, z: float,
                   camera: Camera) -> tuple[float, float, bool]:
    """Where the rope leaves the picture, if it does.

    At CLOSE framing the believed pose is essentially never inside the main frame: at
    5:45 the machine is on the rim of a lethal disc and believes it is sixty-five cells
    away beside deposit A.
    """
    cx, cy, fx, fy, sin_el, cos_el = camera
    half_x, half_y = fx * 0.5 * STUB_MARGIN, fy * 0.5 * STUB_MARGIN

    def screen(x: float, y: float) -> tuple[float, float]:
        # The rope is nine cells above the rock, and height lifts a point up the
        # screen: clipping it as though it lay on the floor put the arrowhead outside
        # the frame by the whole of that lift.
        return x - cx, (y - cy) * sin_el + z * cos_el

    sx, sy = screen(gx, gy)
    if abs(sx) <= half_x and abs(sy) <= half_y:
        return gx, gy, False
    ox, oy = screen(px, py)
    dx, dy = sx - ox, sy - oy
    # The machine is the subject, so the rope starts inside the frame: the exit is the
    # nearer of the two slab crossings. Standard slab clip, in screen units.
    u = 1.0
    if abs(dx) > 1e-9:
        u = min(u, ((half_x if dx > 0.0 else -half_x) - ox) / dx)
    if abs(dy) > 1e-9:
        u = min(u, ((half_y if dy > 0.0 else -half_y) - oy) / dy)
    u = min(max(u, 0.02), 1.0)
    return px + (gx - px) * u, py + (gy - py) * u, u < 0.999
