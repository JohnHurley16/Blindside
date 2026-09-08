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

Down the right-hand edge, two numbers of the same size under near-identical labels --
`IT IS WRONG BY 34` and `IT THINKS IT IS WRONG BY 1` -- which is the whole game in four
words and two integers with no vocabulary to learn (`readout.py`). Before any of it,
twenty-one words for six seconds (`cold_open.py`). And every string on the screen lives
in four `Text` visuals rather than twenty-two (`text_group.py`), which is what pays for
the rest: it took the median frame from 29.3 ms to 20.0 at 5:41.

What this class may see: `MatchView`, which yields Beliefs, Policies and a frozen
`StageFrame`. There is no `Sim` here and no `World` reachable from anything it holds.

Camera: the director drives it, except for six seconds at the start when the cold open
brings it down from 90 degrees to 72. Slice 1 binds no mouse. R sends Recall.
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
from ..match.stage_frame import StageFrame, StageMachine
from . import palette
from .belief_scene import BeliefScene
from .cold_open import ColdOpen
from .director import Director
from .event_feed import EventFeed
from .minimap import Minimap
from .readout import Readout
from .shapes import ring
from .status_panel import StatusPanel
from .taught_rule import TaughtRule
from .text_group import BODY, HEAD, TextGroup
from .timeline import TimelineView
from .tree_panel import TreePanel
from .tree_path import lit_lines
from .truth_panel import TruthPanel

# Draw order among the canvas overlay's children. The three ViewBoxes and the panel
# grounds sit at 0; the cold open's scrim goes over all of them, and the chrome text goes
# over the scrim, because the card's own five lines live in the same four `Text` visuals
# as the rail's and cannot be hidden by hiding a visual.
SCRIM_ORDER: int = 90
CHROME_ORDER: int = 95

FRIENDLY: dict[str, str] = {"DA": "deposit A", "DB": "deposit B",
                            "S": "the shaft", "HOME": "the shaft"}
# Six rows became four. `IT THINKS IT KNOWS WHERE IT IS TO  within 8 cells` is the
# readout's right-hand number said again in more words, at a third of the size, and one
# of them had to go; `MAP IT HAS BUILT  3900 points, 12 pings` is an engineer's row -- a
# stranger cannot use a point count for anything, and 3.5 is blunt that a non-engineer
# reads that sort of line as noise.
STATUS_LABELS: tuple[str, ...] = ("IT IS CARRYING", "CONDITION",
                                  "LAST POSITION FIX", "YOUR ONE COMMAND")
CONDITION_ROW: int = 1
# THE-MACHINERY.md 4.7's second mark: the machine's own damage as a number and a bar.
# Second in the rail rather than last, because it is the answer to the note the gate
# failed on and a row below the fold is not an answer. It is what it is CARRYING and
# then what STATE it is in, which is the order a person asks those two questions in.
MAIN_TITLE: str = "THE CAVE"
MAIN_SUBTITLE: str = "what is actually there"
INSET_TITLE: str = "ITS MAP     what it thinks is there"


class View:
    def __init__(self, match: MatchView, audio: object | None = None, show: bool = True,
                 size: tuple[int, int] = (T.CANVAS_W, T.CANVAS_H),
                 rule: TaughtRule | None = None) -> None:
        """`rule` is the tree the player runs on, rendered by the seam, for the rail:
        the machine she watches is one she taught, and the rail shows the rule and
        lights the path it took at each decision point. None when there is no
        induct binary to render it."""
        self.match: MatchView = match
        self.audio = audio
        self.rule: TaughtRule | None = rule
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
        self.view = scene.ViewBox(parent=overlay, bgcolor=palette.VOID)
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

        self.belief_scene: BeliefScene = BeliefScene(self.view.scene, self.b)
        self._chrome(overlay, w, h)

        self.feed: EventFeed = EventFeed(self.b)
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
    def _chrome(self, overlay: object, w: float, h: float) -> None:
        """Words and grounds -- and every word of it in four `Text` visuals.

        Every `Rectangle` here is touched only in `_layout()`: setting any property on one
        regenerates its geometry and forces a synchronous repaint, and a *static* one costs
        nothing. The strings are a different trap and a bigger one. Twenty-two separate
        `Text` visuals cost about half a millisecond each a frame *just to exist*, whether
        or not anything ever assigns to them, and that was fifteen of a twenty-seven
        millisecond frame. `text_group.py` holds all of them in one visual per type size;
        the four sizes of 6.2 are what makes four enough.
        """
        self.panel_header = self._panel(overlay, w / 2, T.HEADER_H / 2, w, T.HEADER_H)
        self.panel_rail = self._panel(overlay, w - T.RAIL_W / 2, h / 2, T.RAIL_W, h)
        self.panel_timeline = self._panel(overlay, w / 2, h - T.TIMELINE_H / 2,
                                          w, T.TIMELINE_H)
        # One px separators, and the only thing on the screen drawn in `rule`.
        self.rules = visuals.Line(parent=overlay, connect="segments", width=1,
                                  color=(*palette.RULE, 1.0))
        self.rules.set_gl_state("translucent", depth_test=False)

        self.text: TextGroup = TextGroup(overlay, order=CHROME_ORDER)
        self.title = self.text.slot(HEAD, "BLINDSIDE", rgb=palette.PRIMARY)
        self.subtitle = self.text.slot(BODY, "nobody is driving it", rgb=palette.SECONDARY)
        self.header_right = self.text.slot(HEAD, " ", rgb=palette.CARGO)
        self.main_title = self.text.slot(HEAD, MAIN_TITLE, rgb=palette.PRIMARY)
        self.main_subtitle = self.text.slot(BODY, MAIN_SUBTITLE, rgb=palette.SECONDARY)
        self.compass = self.text.slot(BODY, "N", rgb=palette.SECONDARY)
        self.inset_title = self.text.slot(BODY, INSET_TITLE, rgb=palette.SECONDARY)

        # Top of the rail, immediately right of the inset: the small picture of the
        # machine's belief and the small claim that belief makes are one saccade apart.
        self.readout: Readout = Readout(self.text, overlay, order=CHROME_ORDER)
        self.status: StatusPanel = StatusPanel(self.text, STATUS_LABELS,
                                               bar_rows=(CONDITION_ROW,), parent=overlay)
        self.timeline: TimelineView = TimelineView(self.text, overlay)
        self.tree: TreePanel | None = (TreePanel(self.text, self.rule)
                                       if self.rule is not None else None)
        # Everything on the screen that is not a string, for the cold open to put away.
        # The two overlay scenes are on it and the main view is not: the cave is what the
        # card's scrim lifts off, and the belief inset at 0:00 holds three rings and a
        # chevron, which is not a picture anyone can learn anything from.
        self.cold: ColdOpen = ColdOpen(
            self.text, overlay, order=SCRIM_ORDER,
            curtain=(self.panel_header, self.panel_rail, self.panel_timeline, self.rules,
                     self.readout.underline, self.status.bars, self.timeline.track,
                     self.timeline.window, self.timeline.marks, self.timeline.playhead,
                     self.view, self.minimap_view))
        self.text.build()

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
        self._retilt()

        self.panel_header.center = (w / 2, T.HEADER_H / 2)
        self.panel_header.width = w
        self.panel_rail.center = (w - T.RAIL_W / 2, h / 2)
        self.panel_rail.height = h
        self.panel_timeline.center = (w / 2, h - T.TIMELINE_H / 2)
        self.panel_timeline.width = w

        # Everything in the group is anchored left, so anything that used to be right- or
        # centre-aligned is given a left x here. That is what collapses the grouping key
        # from (size, weight, anchor) to (size), and therefore twenty-two visuals to four.
        rail_x = w - T.RAIL_W + T.MARGIN
        self.title.at(18.0, T.HEADER_H / 2)
        # Fractions, not fixed offsets: point-sized type scales with the display's DPI
        # and so does the canvas, so a gap stated as a fraction of the width survives
        # both, while `title_x + 190` is a guess that clips on somebody else's monitor.
        self.subtitle.at(w * 0.135, T.HEADER_H / 2)
        self.subtitle.set("nobody is driving it" if w > 760 else " ")
        self.header_right.at(w - T.RAIL_W - 2 * T.MARGIN - 330.0, T.HEADER_H / 2)
        self.main_title.at(main_x, T.HEADER_H + T.TITLE_H / 2)
        self.main_subtitle.at(main_x + main_w * 0.16, T.HEADER_H + T.TITLE_H / 2)
        self.compass.at(main_x + main_w - 14.0, T.HEADER_H + T.TITLE_H / 2)
        self.inset_title.at(inset_x, inset_y - 9.0)

        rail_top = T.HEADER_H + T.MARGIN + 8.0
        self.readout.move(rail_x, rail_top)
        rule_y = rail_top + self.readout.height + T.MARGIN
        self.status.move(rail_x, rule_y + T.MARGIN + 6.0)
        separators = [[rail_x, rule_y], [w - T.MARGIN, rule_y]]
        if self.tree is not None:
            # Under the status rows, above the timeline: the rule it was taught, lit
            # along the path of its last decision. What does not fit is hidden, never
            # printed on the strip.
            tree_rule_y = self.status.y + self.status.height + T.MARGIN
            self.tree.move(rail_x, tree_rule_y + T.MARGIN + 6.0, h - T.TIMELINE_H - T.MARGIN)
            separators += [[rail_x, tree_rule_y], [w - T.MARGIN, tree_rule_y]]
        self.rules.set_data(np.array(separators, dtype=np.float32))
        self.timeline.move(T.MARGIN, h - T.TIMELINE_H + 18.0, max(w - 2 * T.MARGIN, 80.0))
        self.cold.move(w, h, self._main)

    def _retilt(self) -> None:
        """The director frames in cells across the rectangle, so it needs to know how much
        of that width fits in the height: the aspect, undone by the tilt. Re-derived rather
        than cached because the cold open moves the camera from 90 degrees to 72 while the
        minimap's footprint box is already on screen."""
        _, _, main_w, main_h = self._main
        elevation = math.radians(self.truth_view.camera.elevation)
        self.director.vertical_fraction = (main_h / main_w) / max(math.sin(elevation), 1e-3)

    def on_resize(self, ev: object) -> None:
        w, h = self.canvas.size
        self._layout(float(w), float(h))

    # ---- chrome helpers ---------------------------------------------------------------
    @staticmethod
    def _panel(parent: object, cx: float, cy: float, w: float, h: float) -> object:
        return visuals.Rectangle(center=(cx, cy), width=w, height=h,
                                 color=(*palette.PANEL, 0.94), border_color=(*palette.RULE, 0.9),
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
        elapsed = time.perf_counter() - self._wall_clock_zero
        self.present_cold_open(elapsed)
        # Presentation time runs COLD_OPEN_S ahead of match time for the whole match: the
        # card holds the sim at t = 0 rather than running under it, because a stranger
        # reading five lines has not started watching yet.
        self.match.advance_to(max(0.0, elapsed - T.COLD_OPEN_S), max_steps=8)
        self.draw()
        if self.live:
            self.canvas.update()

    def present_cold_open(self, elapsed: float) -> bool:
        """The card, and the camera arriving under it. Returns whether it is still up.

        A branch against the existing wall clock, not a new timer: every attempt in this
        project to own a vispy timer outside `__main__` produced one that fired once or
        never. The recorder owns its own clock and calls this directly, because the gate
        viewer watched a recording and an explanation that only exists live is one she
        never got.
        """
        if self.cold.done:
            return False
        running = self.cold.update(elapsed)
        self.truth_view.camera.elevation = self.cold.elevation(elapsed)
        self._retilt()
        return running

    def draw(self) -> None:
        b, t = self.b, self.match.t
        frame = self.match.stage()
        self.feed.update(t)
        self.belief_scene.draw(t, self.match.policies["player"].target())
        self._draw_truth(frame, b)
        self._draw_panels(frame, b, t)
        self.timeline.update(self.feed, t)
        # One upload per group per frame, and only for the groups something changed in.
        self.text.flush()
        if self.cold.showing:
            self.cold.hold()
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
        self.director.update(frame, dt, self.belief_scene.fix_easing)

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
    # ---- the rail ---------------------------------------------------------------------------
    def _draw_panels(self, frame: StageFrame, b: Belief, t: float) -> None:
        """The rail: two numbers, then four rows, then the header's one line.

        The frame is passed in rather than fetched: `stage()` is not cached, and one
        CONDITION row is not worth building a second 24,000-cell field for.
        """
        # The whole game, in four words and two integers. `error_cells` is the truth
        # channel's; `sigma_pos()` is the machine's own claim about itself; neither is
        # derived from the other and that is the point of putting them at one size.
        fix = b.last_fix
        self.readout.update(frame.error_cells, b.sigma_pos(), t,
                            None if fix is None else fix.t)

        since = b.ticks_since_fix * T.DT
        surprised = fix is not None and fix.surprise >= 2.5 and fix.jump >= 8.0
        if fix is None:
            fix_text = "none yet"
        else:
            fix_text = f"{int(since) // 60}:{int(since) % 60:02d} ago"
        condition, condition_rgb = _condition(frame.player)
        self.status.set((
            f"{b.cargo} of {T.CARGO_CAPACITY} LOADS",
            condition,
            fix_text,
            "SPENT" if self.match.recall_used else "READY - PRESS R",
        ), (
            palette.CARGO if b.cargo else palette.PRIMARY,
            condition_rgb,
            palette.LIE if surprised or since > 60.0 else palette.PRIMARY,
            palette.TERTIARY if self.match.recall_used else palette.PRIMARY,
        ))
        # The meter's colour is the *damage*, so an undamaged machine's full bar is drawn
        # in tertiary. A full-width white rule across the rail for "nothing has happened
        # yet" is the loudest mark on the screen saying the quietest thing, and 6.3 puts
        # a meter that is not moving in the ambient layer.
        self.status.set_bars(
            (max(0.0, 1.0 - frame.player.damage),),
            (condition_rgb if frame.player.damage > T.DAMAGE_TINT_FROM else palette.TERTIARY,))

        result = self.match.result
        if self.match.over and result is not None:
            header, rgb = f"OVER - {result.player_outcome} - CARGO {result.cargo}", palette.PRIMARY
        elif t >= T.EXTRACT_WINDOW_OPENS:
            header, rgb = "EXTRACTION WINDOW OPEN", palette.CARGO
        else:
            left = T.EXTRACT_WINDOW_OPENS - t
            header = f"EXTRACTION OPENS IN {int(left) // 60}:{int(left) % 60:02d}"
            rgb = palette.CARGO
        self.header_right.set(header)
        self.header_right.tint(rgb)
        self._draw_rule()

    def _draw_rule(self) -> None:
        """Light the rule's lines along the path the last decision walked. The path
        is re-read from the recorded stop the seam's way (`tree_path`), so the lit
        leaf is the action the seam would choose there -- which is the action the
        policy chose, or the rail is visibly wrong."""
        if self.tree is None or self.rule is None:
            return
        policy = self.match.policies["player"]
        lit: list[int] = []
        if policy.decisions and not policy.recalled:
            last = policy.decisions[-1]
            lit, _ = lit_lines(self.rule.root, self.match.registry, self.rule.params,
                               last.predicates, last.raw)
        self.tree.update(lit, policy.recalled)

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

        # Warm over cool. The reveal used to draw the true walls in red over a grey map,
        # which put a second meaning on the one colour that now means only lethal; and it
        # drew the flooded cells as a third layer, which at this size is a dark blue haze
        # over a dark blue map. The reveal is the true *outline* over the map the machine
        # built, and that is one mark.
        walls = np.column_stack([r.walls, np.full(len(r.walls), -0.1)])
        wall_vis = self._over_the_cave(visuals.Markers(parent=s))
        wall_vis.set_data(walls, face_color=(*palette.WARM_DIM, 0.75), size=2.5, edge_width=0)
        self.reveal_visuals.append(wall_vis)

        for name, colour, width in (("player", (*palette.BONE, 0.90), 2),
                                    ("rival", (*palette.EMBER, 0.55), 1.5)):
            path = r.truth_trail.get(name)
            if path:
                self.reveal_visuals.append(self._over_the_cave(visuals.Line(
                    parent=s, pos=np.array([(x, y, 0.3) for x, y, _ in path]),
                    color=colour, width=width)))

        ax, ay, ar = r.ancient
        self.reveal_visuals.append(self._over_the_cave(
            visuals.Line(parent=s, pos=ring(ax, ay, ar, z=0.3),
                         color=(*palette.HAZARD, 0.9), width=2)))
        ends = np.array([[x, y, 0.35] for (x, y, _, _) in r.agents.values()])
        end_vis = self._over_the_cave(visuals.Markers(parent=s))
        end_vis.set_data(ends, face_color=(*palette.WARM_DIM, 0.95), size=12, symbol="x")
        self.reveal_visuals.append(end_vis)

        own = np.array([[x, y, 0.35] for (x, y, owner) in r.beacons.values() if owner == "player"])
        if len(own):
            beacon_vis = self._over_the_cave(visuals.Markers(parent=s))
            beacon_vis.set_data(own, face_color=(*palette.WARM_DIM, 0.90), size=7, symbol="diamond")
            self.reveal_visuals.append(beacon_vis)

        for dx, dy in r.deposits.values():
            self.reveal_visuals.append(self._over_the_cave(
                visuals.Line(parent=s, pos=ring(dx, dy, 3, n=24, z=0.3),
                             color=(*palette.CARGO, 0.85), width=2)))

    # ---- offscreen -----------------------------------------------------------------------------
    def snapshot(self, path: str) -> None:
        self.draw()
        io.write_png(path, self.canvas.render())


# ---- the rail -------------------------------------------------------------------------------------
def _condition(subject: StageMachine) -> tuple[str, tuple[float, float, float]]:
    """The CONDITION row: hull remaining, named after the rung that has actually broken
    rather than in words chosen for how they sound.

    "hurt" starts where the transducer goes short (DAMAGE_RANGE_FROM, 0.20) and names the
    consequence rather than the part -- "seeing less far" fits the 300 px rail, where
    4.7's "odometry unreliable" was clipped at "unrel", and it is now also the only true
    sentence: the odometry effect was cut when it failed THE-MACHINERY 11's own A/B, and
    a row that still said "drifting faster" would be describing a mechanic that no longer
    exists. "limping" starts where the drive goes (DAMAGE_SPEED_FROM, 0.30). Between the
    two the number is the only thing that moves, and it is hull remaining, so the 0.493
    dose the 5:41 near miss delivers reads as "limping, 51%".

    In Phase 1 this is truth: no self-report exists yet and no predicate reads it. Phase
    3's `Return::SelfReport` is where the agent learns the number, through a sensor, so
    it can be wrong -- and this row is where that will show.
    """
    if not subject.alive:
        return "wrecked", palette.KILL
    hull = int(round((1.0 - subject.damage) * 100.0))
    if subject.damage < T.DAMAGE_HURT_FROM:
        return "unhurt", palette.PRIMARY
    if subject.damage < T.DAMAGE_LIMPING_FROM:
        return f"hurt {hull}% - seeing less far", palette.LIE
    return f"limping, {hull}%", palette.HURT


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
