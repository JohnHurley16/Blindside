"""The teach window: the machine's own map, and the question it stops to ask.

Belief only, on purpose. A demonstration is the player choosing on what the machine
believes -- PHASE-2-OPEN-QUESTIONS.md (h) -- and the trace records nothing else, so a
player who chose on the true cave would be teaching a rule the induction cannot see.
The truth channel is never switched on for this window: the `Sim` behind it is built
with `stage=False`, so there is no frame to draw even by mistake. The spectator
display, truth beside belief, is for watching the machine run the rule afterwards.

Three regions. The main one is the belief scene the spectator display keeps in its
inset (`belief_scene.py`), given the whole rectangle. The rail is the block panel:
every enabled predicate with its value and raw number, the actions as numbered keys.
The header is the clock, which stops while the machine waits, and why it stopped.

Keys: a number chooses that action, when it is offered; Q or Escape closes the
window. R does nothing here -- Recall is not a block, and a demonstration is the
player's choices and nothing else.
"""
from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np
from vispy import io, scene
from vispy.scene import visuals

from .. import tuning as T
from ..belief.belief import Belief
from ..demo.trace_writer import TraceWriter
from ..match.match_view import MatchView
from ..policy.block_registry import BlockRegistry
from ..policy.stop_view import StopView
from . import palette
from .belief_scene import BeliefScene
from .block_panel import BlockPanel
from .text_group import BODY, DISPLAY, HEAD, MICRO, TextGroup

CHROME_ORDER: int = 95
FOOTER_H: float = 60.0
BELIEF_ELEVATION_DEG: float = 58.0     # the inset's own camera, unchanged
BELIEF_CELLS_ACROSS: float = 240.0     # the whole 200x120 cave across the main view, with margin
TITLE: str = "BLINDSIDE"
SUBTITLE: str = "teach it: when it stops, press a number"
MAIN_TITLE: str = "ITS MAP"
MAIN_SUBTITLE: str = "what it thinks is there - and all you get to see"


class TeachView:
    """The window. Reads a `MatchView` and answers its stops with the keys."""

    def __init__(self, match: MatchView, registry: BlockRegistry, workdir: Path,
                 show: bool = True, size: tuple[int, int] = (T.CANVAS_W, T.CANVAS_H)) -> None:
        self.match: MatchView = match
        self.registry: BlockRegistry = registry
        self.workdir: Path = workdir
        self.b: Belief = match.beliefs["player"]
        self.size: tuple[int, int] = size
        w, h = size

        self.canvas = scene.SceneCanvas(title="BLINDSIDE - teach it", size=size,
                                        bgcolor=palette.VOID, keys=None, show=show)
        overlay = self.canvas.scene

        self.view = scene.ViewBox(parent=overlay, bgcolor=palette.VOID)
        camera = scene.TurntableCamera(elevation=BELIEF_ELEVATION_DEG, azimuth=0, fov=0, up="z")
        camera.center = (100, 60, 0)
        self.view.camera = camera
        self.view.interactive = False
        self.scene: BeliefScene = BeliefScene(self.view.scene, self.b)

        # ---- chrome, in the shared text group ----
        self.panel_header = self._panel(overlay, w / 2, T.HEADER_H / 2, w, T.HEADER_H)
        self.panel_rail = self._panel(overlay, w - T.RAIL_W / 2, h / 2, T.RAIL_W, h)
        self.panel_footer = self._panel(overlay, w / 2, h - FOOTER_H / 2, w, FOOTER_H)
        self.text: TextGroup = TextGroup(overlay, order=CHROME_ORDER)
        self.title = self.text.slot(HEAD, TITLE, rgb=palette.PRIMARY)
        self.subtitle = self.text.slot(BODY, SUBTITLE, rgb=palette.SECONDARY)
        self.main_title = self.text.slot(HEAD, MAIN_TITLE, rgb=palette.PRIMARY)
        self.main_subtitle = self.text.slot(BODY, MAIN_SUBTITLE, rgb=palette.SECONDARY)
        self.clock = self.text.slot(DISPLAY, "0:00", rgb=palette.PRIMARY)
        self.clock_note = self.text.slot(MICRO, "the match clock", rgb=palette.SECONDARY)
        self.stopped = self.text.slot(HEAD, " ", rgb=palette.PRIMARY)
        self.stopped_why = self.text.slot(BODY, " ", rgb=palette.SECONDARY)
        self.stops_count = self.text.slot(BODY, " ", rgb=palette.SECONDARY)
        self.message = self.text.slot(BODY, " ", rgb=palette.SECONDARY)
        self.hint = self.text.slot(BODY, " ", rgb=palette.PRIMARY)
        self.blocks: BlockPanel = BlockPanel(self.text, registry, match.spec)
        self.text.build()

        self._main: tuple[float, float, float, float] = (0.0, 0.0, float(w), float(h))
        self._zero: float | None = None
        self._paused_at: float | None = None
        self._last_message: str = ""
        self._n_log: int = 0
        self.live: bool = show
        self.quit: bool = False
        self.trace_path: Path | None = None
        self.canvas.events.key_press.connect(self.on_key)
        self.canvas.events.resize.connect(self.on_resize)
        self._layout(float(w), float(h))

    # ---- chrome helpers ---------------------------------------------------------------
    @staticmethod
    def _panel(parent: object, cx: float, cy: float, w: float, h: float) -> object:
        return visuals.Rectangle(center=(cx, cy), width=w, height=h,
                                 color=(*palette.PANEL, 0.94), border_color=(*palette.RULE, 0.9),
                                 border_width=1, parent=parent)

    def _layout(self, w: float, h: float) -> None:
        main_x, main_y = T.MARGIN, T.HEADER_H + T.TITLE_H
        main_w = max(w - 3 * T.MARGIN - T.RAIL_W, 200.0)
        main_h = max(h - T.HEADER_H - T.TITLE_H - FOOTER_H - T.MARGIN, 150.0)
        self._main = (main_x, main_y, main_w, main_h)
        self.view.pos = (main_x, main_y)
        self.view.size = (main_w, main_h)
        self.view.camera.scale_factor = _scale_for(BELIEF_CELLS_ACROSS, main_w, main_h)

        self.panel_header.center = (w / 2, T.HEADER_H / 2)
        self.panel_header.width = w
        self.panel_rail.center = (w - T.RAIL_W / 2, h / 2)
        self.panel_rail.height = h
        self.panel_footer.center = (w / 2, h - FOOTER_H / 2)
        self.panel_footer.width = w

        rail_x = w - T.RAIL_W + T.MARGIN
        self.title.at(18.0, T.HEADER_H / 2)
        self.subtitle.at(w * 0.135, T.HEADER_H / 2)
        self.main_title.at(main_x, T.HEADER_H + T.TITLE_H / 2)
        self.main_subtitle.at(main_x + main_w * 0.16, T.HEADER_H + T.TITLE_H / 2)
        # The clock and the reason it stopped: top of the rail, where the spectator
        # display keeps its two numbers.
        rail_top = T.HEADER_H + T.MARGIN + 8.0
        self.clock.at(rail_x, rail_top + 18.0)
        self.clock_note.at(rail_x, rail_top + 48.0)
        self.stopped.at(rail_x, rail_top + 84.0)
        self.stopped_why.at(rail_x, rail_top + 108.0)
        self.stops_count.at(rail_x, rail_top + 130.0)
        self.blocks.move(rail_x, rail_top + 168.0)
        self.message.at(18.0, h - FOOTER_H + 20.0)
        self.hint.at(18.0, h - FOOTER_H + 42.0)

    def on_resize(self, ev: object) -> None:
        w, h = self.canvas.size
        self._layout(float(w), float(h))

    # ---- input ------------------------------------------------------------------------
    def on_key(self, ev: object) -> None:
        key = getattr(ev, "key", None)
        if key is None:
            return
        self.press(str(key.name).lower())

    def press(self, name: str) -> None:
        """A key by name -- from the window, or from a scripted snapshot."""
        if name in ("escape", "q"):
            self.quit = True
            self.canvas.close()
            return
        if not name.isdigit():
            return
        stop = self.match.stop
        if stop is None:
            return
        index = int(name) - 1
        actions = self.match.spec.enabled_actions
        if not 0 <= index < len(actions):
            return
        action = actions[index]
        if not stop.available.get(action, True):
            self._say(f"{self.registry.action(action).label}: nothing to do here; pick another")
            return
        self.match.answer(action)
        self._say(f"you chose: {self.registry.action(action).label}")
        self.draw()
        if self.live:
            self.canvas.update()

    # ---- frame ------------------------------------------------------------------------
    def reset_clock(self) -> None:
        self._zero = None
        self._paused_at = None

    def advance(self) -> None:
        """One frame of the live window. The match clock runs on the wall clock and
        stops while a question is open: the paused span is taken out of the clock's
        origin when the answer comes, so the sim does not sprint to catch up."""
        now = time.perf_counter()
        if self._zero is None:
            self._zero = now
        if self.match.paused:
            if self._paused_at is None:
                self._paused_at = now
        else:
            if self._paused_at is not None:
                self._zero += now - self._paused_at
                self._paused_at = None
            self.match.advance_to(now - self._zero, max_steps=8)
        self.draw()
        if self.live:
            self.canvas.update()

    def run_to_stop(self) -> StopView | None:
        """No wall clock: straight to the next stop, for a snapshot."""
        stop = self.match.advance_to_stop()
        self.draw()
        return stop

    def draw(self) -> None:
        match, b, t = self.match, self.b, self.match.t
        stop = match.stop
        self.scene.draw(t, match.policies["player"].target())
        self.clock.set(f"{int(t) // 60}:{int(t) % 60:02d}")
        self.clock.tint(palette.PRIMARY if stop is None else palette.SECONDARY)
        self.clock_note.set("stopped while it asks" if stop is not None else "the match clock")
        decisions = match.policies["player"].decisions
        recorded = sum(1 for d in decisions if d.ran)
        if stop is not None:
            self.stopped.set("IT HAS STOPPED")
            self.stopped_why.set(self._why(stop.reason))
            self.stops_count.set(f"stop {recorded + 1}")
            self.hint.set("   ".join(
                f"[{i + 1}] {self.registry.action(a).label}"
                for i, a in enumerate(match.spec.enabled_actions) if stop.available.get(a, True))
                + "     Q quit")
        elif match.over:
            result = match.result
            self.stopped.set("OVER")
            self.stopped_why.set(f"{result.player_outcome}, cargo {result.cargo}" if result else " ")
            self.stops_count.set(f"{recorded} stops recorded")
            self.hint.set("Q to close; the trace is written when you do")
        else:
            self.stopped.set(" ")
            self.stopped_why.set(" ")
            self.stops_count.set(f"{recorded} stops so far" if recorded else " ")
            self.hint.set("it is driving itself; it will stop when it has something to ask")
        self.blocks.update(stop, b, t)
        self._read_log()
        self.text.flush()

    def _read_log(self) -> None:
        """The belief log's own lines, as the footer's message, so what the machine
        is doing between stops -- loading, escaping a wall, searching -- is said."""
        log = self.b.log
        while self._n_log < len(log):
            _, text = log[self._n_log]
            self._n_log += 1
            if " -> " in text or text.startswith("fix ") or text.startswith("drop ") \
                    or text.startswith("new contact") or text == "ping":
                continue
            self._say(text)

    def _say(self, text: str) -> None:
        self._last_message = text
        self.message.set(text)

    def _why(self, reason: str) -> str:
        kind, _, what = reason.partition(":")
        if kind == "rose":
            return f"because: {self.registry.predicate(what).label}"
        if kind == "ended":
            return f"because {self.registry.action(what).label} ended"
        if kind == "start":
            return "the match has begun"
        return "it waited, and is asking again"

    # ---- the trace ----------------------------------------------------------------------
    def finish(self) -> Path | None:
        """Write the demonstration. After the end, whole; after a quit, what there is."""
        match = self.match
        decisions = [d for d in match.policies["player"].decisions if d.ran]
        if not decisions:
            print("no decisions were made; nothing to write")
            return None
        trace = TraceWriter.from_match(match, quit_at=None if match.over else match.t)
        folder = self.workdir / "traces"
        index = len(list(folder.glob(f"trace-seed-{match.seed}*.json"))) if folder.is_dir() else 0
        name = f"trace-seed-{match.seed}.json" if index == 0 else f"trace-seed-{match.seed}-{index}.json"
        self.trace_path = TraceWriter.write(trace, folder / name)
        assert trace.outcome is not None
        print(f"demonstration: seed {match.seed}, {len(trace.steps)} stops, "
              f"success={trace.outcome.success} lost={trace.outcome.lost} "
              f"ticks={trace.outcome.ticks} ({trace.outcome.reason})")
        return self.trace_path

    # ---- offscreen -----------------------------------------------------------------------------
    def snapshot(self, path: str) -> None:
        self.draw()
        io.write_png(path, self.canvas.render())


def _scale_for(cells: float, w: float, h: float) -> float:
    """`scale_factor` that puts `cells` across the rectangle's width; view.py's."""
    return cells * h / w if w > h else cells
