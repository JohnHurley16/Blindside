"""The Assayer as an object you can look at. THE-MACHINERY.md sections 2 and 3.

A survey machine bolted into the bedrock: three legs, a mast, a ribbed array on a
boom, a counterweight, and a hammer that rides the mast. It is dead iron and it is
part of the world, so it is drawn in `ROCK_LIT` and `WARM_DIM` and never in `HAZARD` --
only the *field* is magenta (section 2.1). That is what stops the object being a
magenta blob, and it is why the quiet state has to read as finished rather than as
menacing: if the dormant state already looks like a warning, the warning has nowhere
to go.

**The one rule this file obeys, and it is measured (section 2.2).** `Mesh.set_data` is
a fixed 21.2 ms whether it moves 96 triangles or 2000, and a fresh `MatrixTransform`
each frame is 21.8 ms -- either one alone eats 74% of the 60 ms ceiling. Mutating an
existing transform is 3.25 ms, which is the empty-canvas baseline. So every rigid part
here is a static `Mesh` or `Line` built once in `__init__`, and animation is nothing
but three transforms and two line colours. Nothing in `update()` rebuilds geometry.

Three moving marks, in the order of how much they carry, and the order is a fact about
the camera rather than a taste: a world-z displacement projects up-screen at
cos(elevation), which is 0.31x at the default 72 degrees and exactly zero at the top of
the 60-90 clamp.

  1. **the boom slews and points.** Horizontal rotation is elevation-invariant. A
     7-cell arm swinging 36 degrees in 3 s moves its tip 4.4 cells, and the vertical
     drop line under the tip drags that swing across the floor, where it reads at every
     elevation in the clamp.
  2. **the hammer climbs the mast in nine countable clicks**, one a second, which is
     twenty recorded frames each at the recorder's 20 fps.
  3. **the mast band brightens**, 0.12 to 0.95, the same ramp the acoustic signature is
     already on.

The lobe on the floor -- the other half of the warning, and the half that says where is
safe -- is `shock_lobe.py`, because it is drawn from the coupling field and not from
the machine's own geometry.
"""
from __future__ import annotations

import math

import numpy as np
from vispy import scene
from vispy.scene import visuals
from vispy.visuals.transforms import MatrixTransform, STTransform

from .. import tuning as T
from ..ancient_phase import AncientPhase
from ..match.stage_frame import StageAncient
from . import palette

# ---- the parts, as proportions. Section 2.1's table. -------------------------------------
# These are the shape of one object and nothing tunes them independently, so they live
# beside the code that draws them, the way `director.py` keeps its hold times -- against
# `tuning.py`, which carries the numbers that move a beat.
MAST_FLATS: float = 1.6              # across the flats: a mast, not a pole
MAST_BASE_Z: float = 1.2             # where the legs hand off to the mast
HUB_R: float = 1.0                   # the leg hub, at MAST_BASE_Z
FOOT_R: float = 2.6                  # where a leg reaches the rock
LEG_HUB_W: float = 0.70              # a leg is wider where it is loaded
LEG_FOOT_W: float = 0.45
PAD_CELLS: float = 0.8               # the anchor pad squares, bolted into the bedrock
BOLT_R: float = 3.4                  # the old service platform, as eight bolt heads
BOLT_COUNT: int = 8
BOOM_Z: float = 9.0                  # the array rides above the 8-cell wall line, so which
                                     # way it points is readable from the next chamber
BOOM_SPINE_W: float = 0.9
RIB_COUNT: int = 5
RIB_SPACING: float = 1.4
RIB_ROOT_W: float = 2.4              # the array tapers, so the tip is the narrow end and
RIB_TIP_W: float = 1.2               # the arm reads as pointing rather than as a bar
RIB_HOT: float = 0.20                # outer fifth of each rib, in HAZARD at 0.25: the only
                                     # magenta on the machine, and it is on the emitter
WEIGHT_CELLS: float = 2.2            # the counterweight stub, opposite the boom
WEIGHT_RIB: float = 1.6
WEIGHT_W: float = 0.6
HAMMER_FLATS: float = 2.8            # a collar riding the mast; its z is the animation.
HAMMER_H: float = 1.0                # Section 2.1 says 2.0 across, which against a 1.6-cell
                                     # mast is 0.2 cells of clearance -- 7 px at CLOSE and
                                     # nothing at WIDE, so the countable mark read as a
                                     # brightness change on the mast rather than as a mass
                                     # going up it. Measured and widened until the collar is
                                     # unambiguously a separate part.
BAND_CELLS: float = 0.6              # the top of the mast: the quiet breathe lives here
                                     # rather than on the floor, where it read as a warning

_TAU: float = 2.0 * math.pi


class Assayer:
    """The machine, drawn once and thereafter moved.

    `parent` is the truth scene. Everything is built in machine-local coordinates and
    put in the world by the root node's translation, so the strike recoil is one number
    on one transform.
    """

    def __init__(self, parent: object, ancient: StageAncient) -> None:
        self.x: float = ancient.x
        self.y: float = ancient.y

        # The recoil rides here: section 3 says the rig jolts down 0.4 cells on the
        # blow and recovers over half a second, and that is the whole of the strike as
        # far as the machine's body is concerned.
        self.root: scene.Node = scene.Node(parent=parent)
        self.root.transform = STTransform(translate=(self.x, self.y, 0.0))

        # The boom, its ribs, its counterweight and the drop line under its tip. One
        # node, one rotation, and it is the loudest thing the machine does.
        self.rotor: scene.Node = scene.Node(parent=self.root)
        self.rotor.transform = MatrixTransform()

        verts, faces, colours = _mesh(_footing() + _mast())
        self.body: object = visuals.Mesh(vertices=verts, faces=faces,
                                         vertex_colors=colours, parent=self.root)
        self.body.set_gl_state("opaque", depth_test=True, cull_face=False)

        points, line_colours = _segments(_pads())
        self.pads: object = visuals.Line(parent=self.root, connect="segments", width=1.6,
                                         pos=points, color=line_colours)

        self.bolts: object = visuals.Markers(parent=self.root)
        ring = np.array([[math.cos(_TAU * k / BOLT_COUNT) * BOLT_R,
                          math.sin(_TAU * k / BOLT_COUNT) * BOLT_R, 0.05]
                         for k in range(BOLT_COUNT)], dtype=np.float32)
        self.bolts.set_data(ring, face_color=(*palette.WARM_DIM, 0.5), size=4.0,
                            edge_width=0.0)

        points, line_colours = _segments(_boom() + _counterweight() + _drop_line())
        self.arm: object = visuals.Line(parent=self.rotor, connect="segments", width=1.8,
                                        pos=points, color=line_colours)

        verts, faces, colours = _mesh(_hammer())
        self.hammer: object = visuals.Mesh(vertices=verts, faces=faces,
                                           vertex_colors=colours, parent=self.root)
        self.hammer.set_gl_state("opaque", depth_test=True, cull_face=False)
        self.hammer.transform = STTransform(translate=(0.0, 0.0, MAST_BASE_Z))

        self.band: object = visuals.Line(parent=self.root, connect="segments", width=3.0,
                                         pos=_band_points())

        # Depth-tested, unlike every other overlay in the truth scene: this is a body in
        # the cave and a wall in front of it should hide it. The mast is three cells
        # above the wall line, so the part that says which way it points never can be.
        for visual in (self.pads, self.bolts, self.arm, self.band):
            visual.set_gl_state("translucent", depth_test=True)        # type: ignore[attr-defined]
        for index, visual in enumerate((self.body, self.pads, self.bolts, self.arm,
                                        self.hammer, self.band)):
            visual.order = T.ASSAYER_DRAW_ORDER + index                # type: ignore[attr-defined]

        # What was last written to each transform, so a frame that changes nothing
        # touches nothing. The bearing is constant for seventy-two of every
        # seventy-five seconds and the hammer for fifty-four of them.
        self._bearing: float = float("nan")
        self._hammer_z: float = float("nan")
        self._recoil: float = float("nan")
        self._band: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
        self._matrix: np.ndarray = np.eye(4, dtype=np.float32)

    # ---- one frame ------------------------------------------------------------------
    def update(self, ancient: StageAncient, t: float) -> None:
        self._aim(ancient.bearing_deg)
        self._lift(_hammer_lift(ancient) * T.ANCIENT_HAMMER_RISE_CELLS + MAST_BASE_Z)
        self._jolt(_recoil(ancient))
        self._breathe(ancient, t)

    def _aim(self, bearing_deg: float) -> None:
        if bearing_deg == self._bearing:
            return
        self._bearing = bearing_deg
        c, s = math.cos(math.radians(bearing_deg)), math.sin(math.radians(bearing_deg))
        # vispy multiplies a row vector by the matrix, so this is a z rotation. Written
        # into a matrix this object already owns, then assigned: building a new
        # MatrixTransform each frame measured at 21.8 ms.
        self._matrix[0, 0], self._matrix[0, 1] = c, s
        self._matrix[1, 0], self._matrix[1, 1] = -s, c
        self.rotor.transform.matrix = self._matrix       # type: ignore[attr-defined]

    def _lift(self, z: float) -> None:
        if z == self._hammer_z:
            return
        self._hammer_z = z
        self.hammer.transform.translate = (0.0, 0.0, z)  # type: ignore[attr-defined]

    def _jolt(self, drop: float) -> None:
        if drop == self._recoil:
            return
        self._recoil = drop
        self.root.transform.translate = (self.x, self.y, drop)   # type: ignore[attr-defined]

    def _breathe(self, ancient: StageAncient, t: float) -> None:
        """One band on the top of the mast, and it is the only thing about the dormant
        machine that moves.

        Section 2.3: 0.08-0.14 at 0.1 Hz while it is listening -- the quiet-state
        breathe, moved off the floor and onto the machine, because a ring on the floor
        for seventy-two per cent of the match is most of the reason the object read as
        a circle. Across the wind it goes to 0.95 on the same ramp as the signature.
        """
        phase = ancient.phase
        if phase == AncientPhase.WIND:
            rgb, alpha = palette.HAZARD, 0.12 + 0.83 * ancient.phase_progress
        elif phase == AncientPhase.FIRING:
            rgb, alpha = palette.KILL, 1.0
        elif phase == AncientPhase.LETHAL:
            rgb, alpha = palette.KILL, 0.95 - 0.75 * ancient.phase_progress
        else:
            rgb = palette.HAZARD
            alpha = 0.11 + 0.03 * math.sin(t * 0.1 * _TAU)
        wanted = (*rgb, alpha)
        if wanted != self._band:
            self._band = wanted
            self.band.set_data(color=wanted)             # type: ignore[attr-defined]


# ---- the cycle, as three numbers -----------------------------------------------------------
def _hammer_lift(ancient: StageAncient) -> float:
    """0 at the bottom of the mast, 1 at the top.

    The wind is nine clicks at 1 Hz and each one is a step, not a slope: it snaps up
    over the first fifth of its second and then holds, which is what makes it
    *countable* on a recorded frame rather than a smooth rise nobody counts. A policy
    that hears click seven knows more than one that hears click two.
    """
    phase = ancient.phase
    if phase == AncientPhase.WIND:
        stepped = ancient.phase_progress * T.ANCIENT_CLICKS
        click = min(int(stepped), T.ANCIENT_CLICKS - 1)
        within = min((stepped - click) / T.ANCIENT_RATCHET_FRACTION, 1.0)
        return (click + within * within * (3.0 - 2.0 * within)) / T.ANCIENT_CLICKS
    if phase == AncientPhase.FIRING:
        return 1.0 - ancient.phase_progress          # the whole mast, in three frames
    return 0.0


def _since_blow(ancient: StageAncient) -> float | None:
    """Seconds since the hammer landed, or None if it has not this cycle."""
    if ancient.phase == AncientPhase.FIRING:
        return ancient.phase_progress * T.ANCIENT_FIRE_S
    if ancient.phase == AncientPhase.LETHAL:
        return T.ANCIENT_FIRE_S + ancient.phase_progress * T.ANCIENT_LETHAL_S
    return None


def _recoil(ancient: StageAncient) -> float:
    since = _since_blow(ancient)
    if since is None or since >= T.ANCIENT_RECOIL_S:
        return 0.0
    left = 1.0 - since / T.ANCIENT_RECOIL_S
    return -T.ANCIENT_RECOIL_CELLS * left * left


# ---- geometry, built once --------------------------------------------------------------------
Quad = tuple[np.ndarray, tuple[float, float, float]]
Segment = tuple[float, float, float, float, float, float, tuple[float, float, float, float]]


def _shade(nx: float, ny: float) -> float:
    """The cave's own fixed world light, so the machine is lit like the rock it is
    bolted to and reads as a solid rather than as a flat shape."""
    lit_x = T.CAVE_FACE_SHADES[0] if nx > 0.0 else T.CAVE_FACE_SHADES[2]
    lit_y = T.CAVE_FACE_SHADES[1] if ny > 0.0 else T.CAVE_FACE_SHADES[3]
    weight = abs(nx) + abs(ny)
    if weight < 1e-9:
        return T.CAVE_CAP_SHADE
    return (abs(nx) * lit_x + abs(ny) * lit_y) / weight


def _tint(rgb: tuple[float, float, float], scale: float) -> tuple[float, float, float]:
    return (min(rgb[0] * scale, 1.0), min(rgb[1] * scale, 1.0), min(rgb[2] * scale, 1.0))


def _footing() -> list[Quad]:
    """Three legs 120 degrees apart, hub at r=1.0 and z=1.2, out to r=2.6 on the rock.

    Under alternate mast faces, so the silhouette from any azimuth has a leg in it.
    """
    out: list[Quad] = []
    for k in range(3):
        angle = math.radians(60.0 + 120.0 * k)
        ux, uy = math.cos(angle), math.sin(angle)
        vx, vy = -uy, ux
        quad = np.array([
            [ux * HUB_R + vx * LEG_HUB_W * 0.5, uy * HUB_R + vy * LEG_HUB_W * 0.5, MAST_BASE_Z],
            [ux * HUB_R - vx * LEG_HUB_W * 0.5, uy * HUB_R - vy * LEG_HUB_W * 0.5, MAST_BASE_Z],
            [ux * FOOT_R - vx * LEG_FOOT_W * 0.5, uy * FOOT_R - vy * LEG_FOOT_W * 0.5, 0.0],
            [ux * FOOT_R + vx * LEG_FOOT_W * 0.5, uy * FOOT_R + vy * LEG_FOOT_W * 0.5, 0.0],
        ], dtype=np.float32)
        out.append((quad, _tint(palette.ASSAYER_IRON, _shade(ux, uy))))
    return out


def _mast() -> list[Quad]:
    """A hexagonal prism from the hub to 11 cells, which is three above the wall line.

    That lift is the only thing in the cave that breaks the skyline, and it is what the
    height is *for*: it is not the warning, because at the top of the elevation clamp a
    z displacement projects to nothing at all.
    """
    radius = MAST_FLATS * 0.5 / math.cos(math.radians(30.0))
    out: list[Quad] = []
    for k in range(6):
        a0 = math.radians(30.0 + 60.0 * k)
        a1 = math.radians(30.0 + 60.0 * (k + 1))
        x0, y0 = math.cos(a0) * radius, math.sin(a0) * radius
        x1, y1 = math.cos(a1) * radius, math.sin(a1) * radius
        mid = math.radians(60.0 + 60.0 * k)
        quad = np.array([[x0, y0, MAST_BASE_Z], [x1, y1, MAST_BASE_Z],
                         [x1, y1, T.ANCIENT_MAST_CELLS], [x0, y0, T.ANCIENT_MAST_CELLS]],
                        dtype=np.float32)
        shade = _shade(math.cos(mid), math.sin(mid))
        out.append((quad, _tint(palette.ASSAYER_MAST, shade)))
    return out


def _hammer() -> list[Quad]:
    """A hexagonal collar around the mast. Built at z=0 and lifted by its transform."""
    radius = HAMMER_FLATS * 0.5 / math.cos(math.radians(30.0))
    out: list[Quad] = []
    for k in range(6):
        a0 = math.radians(30.0 + 60.0 * k)
        a1 = math.radians(30.0 + 60.0 * (k + 1))
        x0, y0 = math.cos(a0) * radius, math.sin(a0) * radius
        x1, y1 = math.cos(a1) * radius, math.sin(a1) * radius
        mid = math.radians(60.0 + 60.0 * k)
        quad = np.array([[x0, y0, 0.0], [x1, y1, 0.0],
                         [x1, y1, HAMMER_H], [x0, y0, HAMMER_H]], dtype=np.float32)
        out.append((quad, _tint(palette.ASSAYER_HAMMER,
                                _shade(math.cos(mid), math.sin(mid)))))
    return out


def _pads() -> list[Segment]:
    """The anchor pads: three 0.8-cell squares where the legs meet the bedrock. They
    say bolted-in rather than standing-on, which is the difference between a machine
    that has been here a century and one that walked here."""
    out: list[Segment] = []
    colour = (*_tint(palette.ASSAYER_IRON, 1.2), 0.9)
    half = PAD_CELLS * 0.5
    for k in range(3):
        angle = math.radians(60.0 + 120.0 * k)
        cx, cy = math.cos(angle) * FOOT_R, math.sin(angle) * FOOT_R
        corners = [(cx - half, cy - half), (cx + half, cy - half),
                   (cx + half, cy + half), (cx - half, cy + half)]
        for index in range(4):
            ax, ay = corners[index]
            bx, by = corners[(index + 1) % 4]
            out.append((ax, ay, 0.03, bx, by, 0.03, colour))
    return out


def _boom() -> list[Segment]:
    """The array: two rails, five cross-ribs at 1.4-cell spacing tapering 2.4 to 1.2,
    edge longerons and bay diagonals. The outer fifth of every rib is HAZARD at 0.25.

    Local +x is the aim, so the rotor's z rotation is the survey azimuth directly.
    """
    out: list[Segment] = []
    iron = (*palette.ASSAYER_IRON, 0.95)
    hot = (*palette.HAZARD, 0.25)
    root = MAST_FLATS * 0.5
    tip = T.ANCIENT_BOOM_CELLS
    half = BOOM_SPINE_W * 0.5

    for side in (1.0, -1.0):
        out.append((root, half * side, BOOM_Z, tip, half * side, BOOM_Z, iron))

    xs = [RIB_SPACING * (k + 1) for k in range(RIB_COUNT)]
    widths = [RIB_ROOT_W + (RIB_TIP_W - RIB_ROOT_W) * k / (RIB_COUNT - 1)
              for k in range(RIB_COUNT)]
    for x, width in zip(xs, widths):
        inner = width * 0.5 * (1.0 - RIB_HOT * 2.0)
        outer = width * 0.5
        out.append((x, -inner, BOOM_Z, x, inner, BOOM_Z, iron))
        out.append((x, inner, BOOM_Z, x, outer, BOOM_Z, hot))
        out.append((x, -outer, BOOM_Z, x, -inner, BOOM_Z, hot))

    for index in range(RIB_COUNT - 1):
        x0, x1 = xs[index], xs[index + 1]
        w0, w1 = widths[index] * 0.5, widths[index + 1] * 0.5
        for side in (1.0, -1.0):
            out.append((x0, w0 * side, BOOM_Z, x1, w1 * side, BOOM_Z, iron))
        out.append((x0, half, BOOM_Z, x1, -half, BOOM_Z, iron))
    return out


def _counterweight() -> list[Segment]:
    """A 2.2-cell stub opposite the boom with one 1.6-cell rib. It is what makes the
    array read as balanced on a bearing rather than as an arm stuck out of a pole, and
    it gives the slew a second thing moving the other way."""
    out: list[Segment] = []
    colour = (*_tint(palette.ASSAYER_IRON, 0.85), 0.95)
    root = -MAST_FLATS * 0.5
    tail = -WEIGHT_CELLS
    half = WEIGHT_W * 0.5
    for side in (1.0, -1.0):
        out.append((root, half * side, BOOM_Z, tail, half * side, BOOM_Z, colour))
    out.append((tail, -WEIGHT_RIB * 0.5, BOOM_Z, tail, WEIGHT_RIB * 0.5, BOOM_Z, colour))
    out.append((root, half, BOOM_Z, tail, -half, BOOM_Z, colour))
    return out


def _drop_line() -> list[Segment]:
    """One vertical from the tip of the boom to the floor.

    Section 2.1 asks for this so the boom's ground position is never ambiguous, and it
    is the mark that carries the slew at the top of the elevation clamp: at 90 degrees
    the boom's own 8.4 cells of height project to nothing, but the foot of this line
    still sweeps 4.4 cells across the floor in three seconds.
    """
    return [(T.ANCIENT_BOOM_CELLS, 0.0, BOOM_Z, T.ANCIENT_BOOM_CELLS, 0.0, 0.0,
             (*palette.ASSAYER_IRON, 0.55))]


def _band_points() -> np.ndarray:
    """The top BAND_CELLS of the mast, as a hexagon at each end plus six verticals."""
    radius = MAST_FLATS * 0.5 / math.cos(math.radians(30.0)) * 1.04
    top = T.ANCIENT_MAST_CELLS
    low = top - BAND_CELLS
    out: list[list[float]] = []
    for k in range(6):
        a0 = math.radians(30.0 + 60.0 * k)
        a1 = math.radians(30.0 + 60.0 * (k + 1))
        x0, y0 = math.cos(a0) * radius, math.sin(a0) * radius
        x1, y1 = math.cos(a1) * radius, math.sin(a1) * radius
        out += [[x0, y0, low], [x1, y1, low], [x0, y0, top], [x1, y1, top],
                [x0, y0, low], [x0, y0, top]]
    return np.array(out, dtype=np.float32)


# ---- primitive assembly ------------------------------------------------------------------------
def _mesh(quads: list[Quad]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    vertices = np.concatenate([quad for quad, _ in quads]).astype(np.float32)
    rgb = np.concatenate([np.tile(np.asarray(colour, dtype=np.float32), (4, 1))
                          for _, colour in quads])
    base = np.arange(len(quads), dtype=np.uint32)[:, None] * 4
    faces = np.concatenate([base + np.array([0, 1, 2], dtype=np.uint32),
                            base + np.array([0, 2, 3], dtype=np.uint32)])
    return vertices, faces, np.column_stack([rgb, np.ones(len(vertices), dtype=np.float32)])


def _segments(segments: list[Segment]) -> tuple[np.ndarray, np.ndarray]:
    points = np.array([[s[0], s[1], s[2]] if end == 0 else [s[3], s[4], s[5]]
                       for s in segments for end in (0, 1)], dtype=np.float32)
    colours = np.array([s[6] for s in segments for _ in (0, 1)], dtype=np.float32)
    return points, colours
