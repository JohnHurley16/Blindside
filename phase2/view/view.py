"""Belief-only display for the junction test.

Three regions: the blocks that exist in this run on the left, the map the agent has
built in the middle, the rule induced from what you did on the right. Words live in
fixed places, so position carries meaning.

**What is drawn during a run is Belief and nothing else.** The junction graph is the
one the agent assembled from what it saw at each stop, drawn at the coordinates it
believed it was standing at; walked passages solid, mouths it has only seen dashed;
the pose estimate with its ellipse; the believed way home. Every one of them is
frequently wrong, and looking at this display is the only way the player has of
finding that out.

Truth appears exactly once: after a run is over, over the top, red, under a banner
that says so. It arrives as a `reveal.TruthSnapshot` -- plain numbers with no route
back to World -- through a callable `__main__` hands in. See `match/invariant.py`,
which names this as the exception and checks that there is no other.

Camera: left drag pans, wheel zooms. The view refits itself when the believed map
grows.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Callable

import numpy as np
from vispy import io, scene
from vispy.scene import visuals

from .. import tuning as T
from ..belief.belief import Belief
from ..policy.block_registry import BlockRegistry
from ..reveal.truth_snapshot import TruthSnapshot
from . import palette
from .block_panel import BlockPanel
from .phase import Phase
from .session_controller import SessionController
from .shapes import dashes, ellipse
from .tree_panel import TreePanel
from .tree_path import lit_lines

HEADER_H: float = 46.0
LEFT_W: float = 316.0
RIGHT_W: float = 430.0
FOOTER_H: float = 62.0

RevealSource = Callable[[], TruthSnapshot | None]


class View:
    """The window. Reads a `SessionController` and draws it."""

    def __init__(self, controller: SessionController, registry: BlockRegistry,
                 reveal: RevealSource | None = None, show: bool = True,
                 size: tuple[int, int] = (1500, 920)) -> None:
        self.controller: SessionController = controller
        self.registry: BlockRegistry = registry
        self.reveal_source: RevealSource | None = reveal
        self.size: tuple[int, int] = size
        w, h = size

        self.canvas = scene.SceneCanvas(title="BLINDSIDE - the junction test", size=size,
                                        bgcolor=palette.BACKGROUND, keys=None, show=show)
        overlay = self.canvas.scene

        self.map = scene.ViewBox(parent=overlay, bgcolor=palette.BACKGROUND)
        self.map.camera = scene.PanZoomCamera(aspect=1)
        s = self.map.scene

        self.route = visuals.Line(parent=s, color=palette.ROUTE, width=7)
        self.walked = visuals.Line(parent=s, connect="segments", color=palette.WALKED, width=2)
        self.unwalked = visuals.Line(parent=s, connect="segments", color=palette.UNWALKED,
                                     width=1.4)
        self.trail = visuals.Line(parent=s, color=palette.TRAIL, width=1)
        self.nodes = visuals.Markers(parent=s)
        self.marks = visuals.Markers(parent=s)
        self.ellipse = visuals.Line(parent=s, color=palette.ELLIPSE, width=1.5)
        self.heading = visuals.Line(parent=s, color=palette.AGENT, width=2)
        self.agent = visuals.Markers(parent=s)
        self.truth_passages = visuals.Line(parent=s, connect="segments",
                                           color=palette.TRUTH_PASSAGE, width=1.6)
        self.truth_trail = visuals.Line(parent=s, color=palette.TRUTH_TRAIL, width=1.6)
        self.truth_marks = visuals.Markers(parent=s)
        for v in (self.route, self.walked, self.unwalked, self.trail, self.ellipse,
                  self.heading, self.truth_passages, self.truth_trail):
            v.set_gl_state("translucent", depth_test=False)
        for v in (self.truth_passages, self.truth_trail, self.truth_marks):
            v.visible = False

        # ---- chrome, built once ----
        self.panel_left = self._panel(overlay, LEFT_W / 2, h / 2, LEFT_W, h)
        self.panel_right = self._panel(overlay, w - RIGHT_W / 2, h / 2, RIGHT_W, h)
        self.panel_header = self._panel(overlay, w / 2, HEADER_H / 2, w, HEADER_H)
        self.panel_footer = self._panel(overlay, w / 2, h - FOOTER_H / 2, w, FOOTER_H)

        self.title = visuals.Text("BLINDSIDE", parent=overlay, pos=(18, HEADER_H / 2),
                                  anchor_x="left", anchor_y="center", color=palette.TITLE,
                                  font_size=12, bold=True)
        self.subtitle = visuals.Text("teach it at the junctions - it runs the rule alone",
                                     parent=overlay, pos=(190, HEADER_H / 2),
                                     anchor_x="left", anchor_y="center",
                                     color=palette.DIM, font_size=8.0)
        self.stage_text = visuals.Text("", parent=overlay, pos=(w - 18, HEADER_H / 2),
                                       anchor_x="right", anchor_y="center",
                                       color=palette.BANNER, font_size=9.5, bold=True)
        # The footer carries the run's note, then what just happened on the left and
        # what the keys do on the right. Prose over the map would print on top of the
        # right-hand panel the moment the window is any narrower than it opened.
        self.note_text = visuals.Text("", parent=overlay, pos=(18, h - FOOTER_H + 20),
                                      anchor_x="left", anchor_y="center",
                                      color=palette.DIM, font_size=8.0)
        self.message_text = visuals.Text("", parent=overlay,
                                         pos=(18, h - FOOTER_H + 42), anchor_x="left",
                                         anchor_y="center", color=palette.HUD, font_size=9.0)
        self.hint_text = visuals.Text("", parent=overlay, pos=(w - 18, h - FOOTER_H + 42),
                                      anchor_x="right", anchor_y="center",
                                      color=palette.KEY, font_size=9.0)
        self.reveal_text = visuals.Text("", parent=overlay,
                                        pos=(LEFT_W + 18, h - FOOTER_H - 22),
                                        anchor_x="left", anchor_y="center",
                                        color=palette.TRUTH_TRAIL, font_size=9.0, bold=True)

        self.blocks: BlockPanel = BlockPanel(overlay, 0.0, HEADER_H, LEFT_W, registry)
        self.tree: TreePanel = TreePanel(overlay, w - RIGHT_W, HEADER_H, RIGHT_W)

        self._cache: dict[str, str] = {}
        self._fit_key: tuple[object, ...] | None = None
        self._revealed_seed: int | None = None
        self.live: bool = show
        self.quit: bool = False
        self.canvas.events.key_press.connect(self.on_key)
        self.canvas.events.resize.connect(self.on_resize)
        self._layout(float(w), float(h))

    # ---- chrome helpers ---------------------------------------------------------------------
    @staticmethod
    def _panel(parent: object, cx: float, cy: float, w: float, h: float) -> object:
        return visuals.Rectangle(center=(cx, cy), width=w, height=h, color=palette.PANEL,
                                 border_color=palette.PANEL_EDGE, border_width=1,
                                 parent=parent)

    def _set(self, key: str, visual: object, text: str) -> None:
        """Only touch a Text when its string actually changed."""
        if self._cache.get(key) != text:
            self._cache[key] = text
            visual.text = text          # type: ignore[attr-defined]

    def _layout(self, w: float, h: float) -> None:
        self.map.pos = (LEFT_W, HEADER_H)
        self.map.size = (max(w - LEFT_W - RIGHT_W, 80), max(h - HEADER_H - FOOTER_H, 80))
        for panel, centre, width, height in (
                (self.panel_left, (LEFT_W / 2, h / 2), LEFT_W, h),
                (self.panel_right, (w - RIGHT_W / 2, h / 2), RIGHT_W, h),
                (self.panel_header, (w / 2, HEADER_H / 2), w, HEADER_H),
                (self.panel_footer, (w / 2, h - FOOTER_H / 2), w, FOOTER_H)):
            panel.center = centre           # type: ignore[attr-defined]
            panel.width = width             # type: ignore[attr-defined]
            panel.height = height           # type: ignore[attr-defined]
        self.stage_text.pos = (w - 18, HEADER_H / 2)
        self.note_text.pos = (18, h - FOOTER_H + 20)
        self.message_text.pos = (18, h - FOOTER_H + 42)
        self.hint_text.pos = (w - 18, h - FOOTER_H + 42)
        self.reveal_text.pos = (LEFT_W + 18, h - FOOTER_H - 22)
        self.blocks.move(0.0, HEADER_H, LEFT_W)
        self.tree.move(w - RIGHT_W, HEADER_H, RIGHT_W)
        self.subtitle.visible = w > 900

    def on_resize(self, ev: object) -> None:
        w, h = self.canvas.size
        self._layout(float(w), float(h))
        self.draw()

    # ---- input -------------------------------------------------------------------------------
    def on_key(self, ev: object) -> None:
        key = getattr(ev, "key", None)
        if key is None:
            return
        name = str(key.name).lower()
        if name in ("escape", "q"):
            self.quit = True
            self.canvas.close()
            return
        before = self.controller.phase
        self.controller.key(name)
        if before is not self.controller.phase or name.isdigit():
            self._fit_key = None
        self.draw()
        if self.live:
            self.canvas.update()

    # ---- frame ---------------------------------------------------------------------------------
    def draw(self) -> None:
        c = self.controller
        stop = c.stop or c.last_stop
        belief = stop.belief if stop is not None else None
        if belief is not None:
            self._draw_belief(belief, c.phase)
        self._draw_reveal()
        self._draw_panels()

    # ---- the believed map -----------------------------------------------------------------------
    def _draw_belief(self, b: Belief, phase: Phase) -> None:
        walked: list[list[float]] = []
        seen: list[np.ndarray] = []
        for node in b.nodes.values():
            for passage in node.passages:
                far = b.nodes.get(passage.far) if passage.far is not None else None
                if passage.walked and far is not None:
                    walked += [[node.x, node.y, 0.0], [far.x, far.y, 0.0]]
                    continue
                stub = T.UNWALKED_STUB_CELLS
                ex = node.x + math.cos(passage.bearing) * stub
                ey = node.y + math.sin(passage.bearing) * stub
                if passage.walked:
                    walked += [[node.x, node.y, 0.0], [ex, ey, 0.0]]
                else:
                    seen += dashes(node.x, node.y, ex, ey, dash=1.8)
        self._segments(self.walked, walked)
        self._segments(self.unwalked, [list(p) for p in seen])

        route: list[list[float]] = []
        if b.current is not None and b.current in b.nodes:
            route = [[b.nodes[n].x, b.nodes[n].y, 0.0]
                     for n in [b.current] + b.route_back() if n in b.nodes]
        if len(route) > 1:
            self.route.set_data(np.array(route))
            self.route.visible = True
        else:
            self.route.visible = False

        points = [[n.x, n.y, 0.0] for n in b.nodes.values()]
        colours = [palette.NODE_HERE if n.id == b.current else palette.NODE
                   for n in b.nodes.values()]
        if points:
            self.nodes.set_data(np.array(points), face_color=np.array(colours), size=7,
                                edge_width=0, symbol="disc")
            self.nodes.visible = True
        else:
            self.nodes.visible = False

        marks: list[list[float]] = []
        mark_colours: list[tuple[float, float, float, float]] = []
        shaft = b.nodes.get(b.shaft)
        if shaft is not None:
            marks.append([shaft.x, shaft.y, 0.0])
            mark_colours.append(palette.SHAFT)
        cargo = b.nodes.get(b.cargo_at) if b.cargo_at is not None else None
        if cargo is not None:
            marks.append([cargo.x, cargo.y, 0.0])
            mark_colours.append(palette.DEPOSIT)
        if marks:
            self.marks.set_data(np.array(marks), face_color=np.array(mark_colours),
                                size=16, edge_width=0, symbol="star")
            self.marks.visible = True
        else:
            self.marks.visible = False

        if len(b.trail) > 1:
            self.trail.set_data(np.array([[x, y, 0.0] for x, y in b.trail]))
            self.trail.visible = True
        else:
            self.trail.visible = False

        along = T.ELLIPSE_SIGMAS * b.sigma_along()
        cross = T.ELLIPSE_SIGMAS * b.sigma_cross()
        self.ellipse.set_data(ellipse(b.x, b.y, along, cross, b.theta))
        self.agent.set_data(np.array([[b.x, b.y, 0.0]]), face_color=palette.AGENT,
                            size=12, symbol="triangle_up", edge_width=0)
        self.heading.set_data(np.array([[b.x, b.y, 0.0],
                                        [b.x + 5 * math.cos(b.theta),
                                         b.y + 5 * math.sin(b.theta), 0.0]]))
        self._fit(b, along, cross, phase)

    @staticmethod
    def _segments(visual: object, points: list[list[float]]) -> None:
        if points:
            visual.set_data(np.array(points))       # type: ignore[attr-defined]
            visual.visible = True                   # type: ignore[attr-defined]
        else:
            visual.visible = False                  # type: ignore[attr-defined]

    def _fit(self, b: Belief, along: float, cross: float, phase: Phase) -> None:
        """Refit only when the map has actually grown, so that a pan survives a redraw."""
        key = (self.controller.stage.number, len(b.nodes), phase, self._revealed_seed)
        if key == self._fit_key:
            return
        self._fit_key = key
        radius = max(along, cross, 8.0)
        xs = [n.x for n in b.nodes.values()] + [b.x - radius, b.x + radius]
        ys = [n.y for n in b.nodes.values()] + [b.y - radius, b.y + radius]
        # z is given so that set_range never asks the scene for its own bounds: a
        # Markers visual that has never been given data raises from inside vispy when
        # it is asked, and several of these are empty until the run is over.
        self.map.camera.set_range(x=(min(xs), max(xs)), y=(min(ys), max(ys)),
                                  z=(-1.0, 1.0), margin=0.12)

    # ---- truth, once the run is over ---------------------------------------------------------------
    def _draw_reveal(self) -> None:
        c = self.controller
        if c.phase is not Phase.RUN_OVER or self.reveal_source is None:
            if c.phase is not Phase.RUN_OVER and self._revealed_seed is not None:
                self._revealed_seed = None
                for v in (self.truth_passages, self.truth_trail, self.truth_marks):
                    v.visible = False
                self._set("reveal", self.reveal_text, "")
            return
        if self._revealed_seed == c.stage.seed:
            return
        snapshot = self.reveal_source()
        if snapshot is None:
            return
        self._revealed_seed = snapshot.seed
        self._segments(self.truth_passages,
                       [c2 for x0, y0, x1, y1 in snapshot.passages
                        for c2 in ([x0, y0, 0.0], [x1, y1, 0.0])])
        if len(snapshot.trail) > 1:
            self.truth_trail.set_data(np.array([[x, y, 0.0] for x, y in snapshot.trail]))
            self.truth_trail.visible = True
        self.truth_marks.set_data(
            np.array([[snapshot.deposit[0], snapshot.deposit[1], 0.0],
                      [snapshot.agent[0], snapshot.agent[1], 0.0]]),
            face_color=np.array([palette.TRUTH_DEPOSIT, palette.TRUTH_AGENT]),
            size=14, edge_width=0, symbol="x")
        self.truth_marks.visible = True
        self._set("reveal", self.reveal_text,
                  f"AFTER THE RUN - THE TRUTH, IN RED. it took {snapshot.misturns} wrong "
                  f"turnings; the cargo was at the yellow cross")
        self._fit_key = None

    # ---- panels ------------------------------------------------------------------------------------
    def _draw_panels(self) -> None:
        c = self.controller
        stage = c.stage
        stop = c.stop
        self._set("stage", self.stage_text,
                  f"RUN {stage.number} OF {len(c.tutorial.stages)}  -  {stage.title}")
        self._set("note", self.note_text, stage.note if c.phase in
                  (Phase.STOP, Phase.RUN_OVER) else "")
        self._set("message", self.message_text, c.message)
        self._set("hint", self.hint_text, c.hints())
        self.blocks.update(stop, c.offered_predicates, c.offered_actions, c.offered_params,
                           waiting=c.phase in (Phase.STOP, Phase.TAKEOVER))

        lit: list[int] = []
        notes: list[str] = []
        flagged = False
        tree = self._tree_dict()
        if tree is not None and c.ghost is not None and c.phase in (
                Phase.GHOST, Phase.SCRUB, Phase.TAKEOVER, Phase.PROMOTED):
            steps = c.ghost.steps
            index = min(c.scrub_index, len(steps) - 1) if steps else -1
            if index >= 0:
                lit, _ = lit_lines(tree["root"], self.registry,
                                   tree.get("params", {}), steps[index].predicates,
                                   steps[index].raw)
                flagged = c.ghost.first_difference == index
                notes.append(f"GHOST, seed {c.ghost.seed}: stop {index} of "
                             f"{len(c.ghost.demonstrated)}")
                notes.append(c.ghost.summary())
                if flagged:
                    notes.append("this is the stop the rule got wrong. Take over here.")
        if c.correction_seconds is not None:
            notes.append(f"scrub to re-induce: {c.correction_seconds:.1f} s of wall clock")
        self.tree.update(c.rendered, lit, flagged, notes)

    def _tree_dict(self) -> dict[str, object] | None:
        induction = self.controller.reinduction or self.controller.induction
        return induction.tree if induction is not None else None

    # ---- offscreen ---------------------------------------------------------------------------------
    def snapshot(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.draw()
        io.write_png(str(path), self.canvas.render())
        return path
