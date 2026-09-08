"""The cave as it really is, with the machine in it. SPECTATOR-DISPLAY.md section 6.4.

Consumes a `StageFrame` and the player's believed pose. It cannot import `truth` and it
cannot name `.world`; `match/invariant.py` rules 3 and 4 prove it. Everything real in
here arrived through the one-way channel in section 4, and the believed pose arrived
from `Belief`, which the renderer has always been allowed to read.

Slice 1 draws eight of the thirteen marks: the cave, the floor, the eleven names, both
machines to scale, both comets, the ghost, the tether, the machinery and its countdown,
and the deposits at their true radius. Beacons, sound rings, the spoof's dashed line
and the believed-machinery disc are later slices.

The machinery is no longer a red disc with a label on it. It is the Assayer -- a body in
`assayer.py` and a pointed field on the floor in `shock_lobe.py` -- and this file owns
only the two things that are neither: the countdown, and the damage a machine is
carrying, which arrives on the glyph as colour, thinning and a sensor head that stops
turning (THE-MACHINERY.md 4.7). Nothing about the cycle's timing moved; the drawing did.

Every overlay is `translucent, depth_test=False` and ordered after the mesh, so the
subject is never lost behind rock; the tether and the chamber names are additionally
lifted above the wall height, which is the same result and is stable under orbit.

The three `Text` visuals here are the only strings on the screen that are **not** in
`text_group.py`'s four, and they cannot be: they are positioned in scene coordinates
inside a camera's ViewBox rather than in canvas pixels. They take their sizes from the
same four-value scale, so the type discipline of 6.2 holds across the whole screen even
though the grouping cannot.
"""
from __future__ import annotations

import math

import numpy as np
from vispy.scene import visuals

from .. import tuning as T
from ..match.stage_frame import StageFrame, StageMachine
from . import palette
from .assayer import Assayer
from .cave_mesh import CaveMesh
from .chamber_names import CHAMBER_LABELS
from .glyph import machine
from .shapes import ring, to_segments
from .shock_lobe import ShockLobe

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
        # Order matters and is stated in `tuning.py`: the scour under the lobe, the lobe
        # under the machine, the machine under everything that is a subject. Built in
        # this order as well as ordered, because two visuals with the same `order` draw
        # in the order they were added.
        self.lobe: ShockLobe = ShockLobe(parent, frame.ancient, frame.grid)
        self.assayer: Assayer = Assayer(parent, frame.ancient)

        self.names = visuals.Text(
            [name for name, _, _ in CHAMBER_LABELS],
            pos=np.array([[x, y, LABEL_Z] for _, x, y in CHAMBER_LABELS]),
            parent=parent, color=(*palette.WARM_DIM, 0.85), font_size=T.TYPE_BODY_PT,
            anchor_x="center", anchor_y="center")

        self.deposits = visuals.Line(parent=parent, connect="segments", width=1.5,
                                     color=(*palette.CARGO, 0.35))
        self.comet_player = visuals.Line(parent=parent, width=2.5)
        self.comet_rival = visuals.Line(parent=parent, width=2.0)
        self.machines = visuals.Line(parent=parent, connect="segments", width=2.0)
        self.tether = visuals.Line(parent=parent, connect="segments", width=2.0)
        self.tether_label = visuals.Text("", parent=parent, pos=(0.0, 0.0, T.TETHER_Z_CELLS),
                                         color=(*palette.LIE, 0.95), font_size=T.TYPE_HEAD_PT,
                                         bold=True, anchor_x="center", anchor_y="bottom")
        self.hazard_label = visuals.Text("", parent=parent, pos=(0.0, 0.0, COUNTDOWN_Z),
                                         color=(*palette.HAZARD, 0.95), font_size=T.TYPE_BODY_PT,
                                         bold=True, anchor_x="center", anchor_y="center")

        overlays = (self.names, self.deposits, self.comet_player, self.comet_rival,
                    self.machines, self.tether, self.tether_label, self.hazard_label)
        for index, visual in enumerate(overlays):
            visual.set_gl_state("translucent", depth_test=False)
            visual.order = T.TRUTH_OVERLAY_ORDER + index

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
        """Both machines, the ghost, and how hurt each of them is.

        THE-MACHINERY.md 4.7's first mark, and the reason it is on the glyph rather than
        beside it: at CAMERA_WIDE_CELLS a machine is nine pixels and no text anywhere on
        this screen can be read, so the meter has to be the shape and colour of the thing
        itself. A shaken machine is thinner (a hatch stroke at a time), redder (walking
        toward KILL), and has stopped looking (the sensor head slows and then stops). A
        stranger reads *that machine is in trouble* with no legend and no glance away, and
        a machine limping home at 40% with cargo aboard reads as exactly that.

        Nothing here is a belief: it is what is true of the machine. What the machine
        itself would be told arrives through a sensor in Phase 3 and can be wrong.
        """
        bx, by, btheta = believed
        drawn: list[tuple[list[tuple[float, float, float, float]], tuple[float, float, float], float]] = [
            (machine(frame.player.x, frame.player.y, frame.player.heading,
                     T.GLYPH_LENGTH_CELLS, filled=True, alive=frame.player.alive,
                     cargo=frame.player.cargo, head=_head(frame.t, frame.player.damage),
                     damage=frame.player.damage),
             _hurt(palette.BONE, frame.player), 1.0),
            (machine(frame.rival.x, frame.rival.y, frame.rival.heading,
                     T.GLYPH_LENGTH_CELLS, filled=True, alive=frame.rival.alive,
                     cargo=frame.rival.cargo, head=-_head(frame.t, frame.rival.damage),
                     damage=frame.rival.damage),
             _hurt(palette.EMBER, frame.rival), 1.0),
            # Hollow, identical geometry, at the pose it believes it holds. Solid is the
            # thing; hollow is a belief about the thing. It is never damaged, because a
            # belief about where you are does not have a hull.
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
        """The Assayer's body, its field, and the one label.

        The drawing is two objects and this method owns neither: `Assayer` moves a boom,
        a hammer and a mast band, and `ShockLobe` paints the floor. What is left here is
        `LETHAL IN 0:07`, kept and treated as an instrument rather than as furniture --
        HAZARD_COUNTDOWN_FROM_S is 15, so the number appears two seconds *after* the boom
        has swung and pointed. That gap is the gate question: ask a tester at -16 s what
        the machine is about to do, before the number exists. If they can say it, the
        label is redundant and goes in Phase 3.
        """
        a = frame.ancient
        self.assayer.update(a, frame.t)
        self.lobe.update(a)

        until = a.seconds_until_lethal
        show = in_main_slot and until <= T.HAZARD_COUNTDOWN_FROM_S and not a.is_lethal
        text = f"LETHAL IN 0:{int(math.ceil(until)):02d}" if show else (
            "LETHAL NOW" if (in_main_slot and a.is_lethal) else "")
        if text != self._hazard_text:                    # gated on the integer second
            self._hazard_text = text
            self.hazard_label.text = text
        # Above the machine rather than beside it -- a machine can stand anywhere on the
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
            # Which side of the rope: whichever is further from the minimap. The label
            # sits in world space and the minimap is a fixed opaque rectangle in the
            # lower left of the frame, so at the spoof -- when the arrow leaves through
            # that very corner -- "-> 34 cells" was drawn under it and read as "lls",
            # while the rail said 34. tuning.py's own note is that the rope and the
            # number are one fact drawn twice and may not disagree; at the beat the
            # display exists for, they did.
            side = 1.0 if _left_of_frame(end_x, end_y, z, camera) else -1.0
            self.tether_label.pos = (end_x + math.sin(back) * 2.6 * side,
                                     end_y - math.cos(back) * 2.6 * side, z + 0.8)
        else:
            self.tether_label.pos = ((px + end_x) / 2.0, (py + end_y) / 2.0, z + 0.8)
        if rgb != self._tether_rgb:
            self._tether_rgb = rgb
            self.tether_label.color = (*rgb, 0.95)
        _show(self.tether_label, bool(text))


def _head(t: float, damage: float) -> float:
    """The sensor head's angle. It slows at 0.45 damage and stops at 0.80.

    The head is the one mark in `glyph.py` that says *alive and still looking*, so its
    rate is the cheapest possible statement that the instruments went before the frame
    did -- which is the whole claim THE-MACHINERY makes about what a shock breaks.
    Closed form rather than integrated, because `--snap` advances the match by minutes
    between draws; the step when damage crosses a threshold is a few degrees of a
    decorative rotation and is not observable.
    """
    rate = HEAD_TURN_DEG_S
    if damage >= T.DAMAGE_HEAD_STOP_FROM:
        rate = 0.0
    elif damage >= T.DAMAGE_HEAD_SLOW_FROM:
        rate *= 0.5
    return math.radians(t * rate) % (2.0 * math.pi)


def _hurt(rgb: tuple[float, float, float], subject: StageMachine) -> tuple[float, float, float]:
    """A machine's colour, walking toward KILL as it takes shock. A wreck is KILL."""
    if not subject.alive:
        return palette.KILL
    if subject.damage <= T.DAMAGE_TINT_FROM:
        return rgb
    return palette.lerp(rgb, palette.HURT,
                        (subject.damage - T.DAMAGE_TINT_FROM) / (1.0 - T.DAMAGE_TINT_FROM))


def _show(visual: object, wanted: bool) -> None:
    """`Node.visible` always calls `update()`, whether or not the value changed."""
    if visual.visible is not wanted:                    # type: ignore[attr-defined]
        visual.visible = wanted                         # type: ignore[attr-defined]


def _left_of_frame(x: float, y: float, z: float, camera: Camera) -> bool:
    """Is this world point in the lower-left quarter of the frame, where the minimap is?

    The minimap is drawn opaque over the main view at a fixed screen position, so a mark
    that lands there is not dimmed, it is gone. Only the tether label moves for it: it is
    the one mark whose position is chosen rather than meant.
    """
    cx, cy, fx, fy, sin_el, cos_el = camera
    sx = (x - cx) / (fx * 0.5)
    sy = ((y - cy) * sin_el + z * cos_el) / (fy * 0.5)
    return sx < -0.25 and sy < -0.15


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
