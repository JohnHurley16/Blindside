"""The shape of the match, as a strip along the bottom.

Every event that happens gets a mark at the time it happened, so the density and
rhythm of the match are visible at a glance and you can see the quiet stretch before
something goes wrong. Only the event happening right now is spelled out in words.
"""
from __future__ import annotations

import numpy as np
from vispy.scene import visuals

from .. import tuning as T
from . import palette
from .event_feed import EventFeed
from .event_kind import EventKind


class TimelineView:
    def __init__(self, parent: object, x: float, y: float, width: float,
                 height: float = 58.0) -> None:
        self.x: float = x
        self.y: float = y
        self.width: float = width
        self.height: float = height
        self.track_y: float = y + height * 0.62

        self.track = visuals.Line(parent=parent, connect="segments",
                                  color=(0.26, 0.31, 0.38, 0.9), width=2)
        self.window = visuals.Line(parent=parent, connect="segments",
                                   color=(0.95, 0.62, 0.25, 0.55), width=6)
        self.marks = visuals.Line(parent=parent, connect="segments", width=2)
        self.playhead = visuals.Line(parent=parent, connect="segments",
                                     color=palette.AGENT, width=2)
        for v in (self.track, self.window, self.marks, self.playhead):
            v.set_gl_state("translucent", depth_test=False)

        self.track.set_data(np.array([[x, self.track_y, 0.0],
                                      [x + width, self.track_y, 0.0]]))
        wx0 = self._px(T.EXTRACT_WINDOW_OPENS)
        wx1 = self._px(T.MATCH_SECONDS)
        self.window.set_data(np.array([[wx0, self.track_y, 0.0], [wx1, self.track_y, 0.0]]))

        self.clock = visuals.Text("", parent=parent, pos=(x, y + 8), anchor_x="left",
                                  anchor_y="center", color=palette.HUD, font_size=10, bold=True)
        self.window_label = visuals.Text("extraction window", parent=parent,
                                         pos=((wx0 + wx1) / 2, self.track_y + 16),
                                         anchor_x="center", anchor_y="center",
                                         color=(0.95, 0.62, 0.25), font_size=7.5)
        self.now = visuals.Text("", parent=parent, pos=(x, y + 8), anchor_x="left",
                                anchor_y="center", color=palette.BANNER, font_size=10, bold=True)
        self.now_detail = visuals.Text("", parent=parent, pos=(x, y + 26), anchor_x="left",
                                       anchor_y="center", color=palette.HUD, font_size=8)
        self._cache: tuple[str, str, str] = ("", "", "")
        self._n_events: int = 0
        self.move(x, y, width)

    def move(self, x: float, y: float, width: float) -> None:
        self.x, self.y, self.width = x, y, width
        self.track_y = y + self.height * 0.62
        self.track.set_data(np.array([[x, self.track_y, 0.0],
                                      [x + width, self.track_y, 0.0]]))
        wx0 = self._px(T.EXTRACT_WINDOW_OPENS)
        wx1 = self._px(T.MATCH_SECONDS)
        self.window.set_data(np.array([[wx0, self.track_y, 0.0],
                                       [wx1, self.track_y, 0.0]]))
        self.window_label.pos = ((wx0 + wx1) / 2, self.track_y + 16)
        self.clock.pos = (x, y + 8)
        self.now.pos = (x + 300, y + 8)
        self.now_detail.pos = (x + 300, y + 26)
        self._n_events = -1

    def _px(self, t: float) -> float:
        return self.x + self.width * min(max(t / T.MATCH_SECONDS, 0.0), 1.0)

    def update(self, feed: EventFeed, t: float) -> None:
        if len(feed.events) != self._n_events:
            self._n_events = len(feed.events)
            segments: list[list[float]] = []
            colours: list[tuple[float, float, float, float]] = []
            for event in feed.events:
                px = self._px(event.t)
                half = 11.0 if event.major else 6.0
                segments.append([px, self.track_y - half, 0.0])
                segments.append([px, self.track_y + half, 0.0])
                rgb = palette.EVENT.get(event.kind, (0.7, 0.75, 0.8))
                alpha = 0.95 if event.major else 0.5
                colours += [(*rgb, alpha)] * 2
            if segments:
                self.marks.set_data(np.array(segments), color=np.array(colours))
                self.marks.visible = True
            else:
                self.marks.visible = False

        px = self._px(t)
        self.playhead.set_data(np.array([[px, self.track_y - 18, 0.0],
                                         [px, self.track_y + 18, 0.0]]))

        left = max(0.0, T.MATCH_SECONDS - t)
        clock = f"{int(t) // 60}:{int(t) % 60:02d}  /  8:00      {int(left) // 60}:{int(left) % 60:02d} left"
        event = feed.latest(t)
        now_text = event.text.upper() if event is not None else ""
        detail = event.detail if event is not None else ""
        if self._cache != (clock, now_text, detail):
            self._cache = (clock, now_text, detail)
            self.clock.text = clock
            self.now.text = now_text
            self.now_detail.text = detail
