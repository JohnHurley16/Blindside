"""The shape of the match, as a strip along the bottom.

Every event that happens gets a mark at the time it happened, so the density and rhythm
of the match are visible at a glance and you can see the quiet stretch before something
goes wrong. Only the event happening right now is spelled out in words.

The clock is Display-sized, because 6.2 lists the match clock beside the two error
numbers as one of the three things on this screen that must be readable in under a
second from across the room. `5:41` is four characters; everything else about the clock
-- how long the match is, how much is left -- is Micro underneath it, because those are
units and not the number.

Every colour here is a value that already means the same thing elsewhere on screen:
`rule` for dead track, `cargo` for the extraction window because extraction is the
objective, `primary` for the playhead because now is not a belief about anything. The
strip used to carry its own amber and its own green and a default grey, none of which
appeared anywhere else.
"""
from __future__ import annotations

import numpy as np
from vispy.scene import visuals

from .. import tuning as T
from . import palette
from .event_feed import EventFeed
from .text_group import BODY, DISPLAY, HEAD, MICRO, Slot, TextGroup

NOW_X: float = 250.0             # px from the strip's left edge to the now-line's column
WINDOW_LABEL_BACK: float = 52.0  # px left of the window's midpoint: everything in the group
                                 # is left-anchored, so a centred label is given a left x
# The four text rows sit ABOVE the track at fixed offsets from the strip's top, rather
# than at fractions of a height that used to land the clock's second line on the pips.
CLOCK_Y: float = 24.0
CLOCK_SUB_Y: float = 58.0
NOW_Y: float = 16.0
NOW_DETAIL_Y: float = 38.0
TRACK_Y: float = 94.0


class TimelineView:
    def __init__(self, group: TextGroup, parent: object, x: float = 0.0, y: float = 0.0,
                 width: float = 100.0, height: float = 58.0, order: int = 0) -> None:
        self.x: float = x
        self.y: float = y
        self.width: float = width
        self.height: float = height
        self.track_y: float = y + TRACK_Y

        self.track = visuals.Line(parent=parent, connect="segments",
                                  color=(*palette.RULE, 1.0), width=2)
        self.window = visuals.Line(parent=parent, connect="segments",
                                   color=(*palette.CARGO, 0.45), width=6)
        self.marks = visuals.Line(parent=parent, connect="segments", width=2)
        self.playhead = visuals.Line(parent=parent, connect="segments",
                                     color=(*palette.PRIMARY, 0.95), width=2)
        for v in (self.track, self.window, self.marks, self.playhead):
            v.set_gl_state("translucent", depth_test=False)
            v.order = order

        self.clock: Slot = group.slot(DISPLAY, "0:00", rgb=palette.PRIMARY)
        self.clock_sub: Slot = group.slot(MICRO, " ", rgb=palette.SECONDARY)
        self.window_label: Slot = group.slot(MICRO, "extraction window", rgb=palette.CARGO)
        self.now: Slot = group.slot(HEAD, " ", rgb=palette.PRIMARY)
        self.now_detail: Slot = group.slot(BODY, " ", rgb=palette.SECONDARY)

        self._n_events: int = -1
        self._has_marks: bool = False
        self.move(x, y, width)

    def move(self, x: float, y: float, width: float) -> None:
        self.x, self.y, self.width = x, y, width
        self.track_y = y + TRACK_Y
        self.track.set_data(np.array([[x, self.track_y, 0.0],
                                      [x + width, self.track_y, 0.0]]))
        wx0 = self._px(T.EXTRACT_WINDOW_OPENS)
        wx1 = self._px(T.MATCH_SECONDS)
        self.window.set_data(np.array([[wx0, self.track_y, 0.0],
                                       [wx1, self.track_y, 0.0]]))
        self.window_label.at((wx0 + wx1) / 2.0 - WINDOW_LABEL_BACK, self.track_y + 16.0)
        self.clock.at(x, y + CLOCK_Y)
        self.clock_sub.at(x, y + CLOCK_SUB_Y)
        self.now.at(x + NOW_X, y + NOW_Y)
        self.now_detail.at(x + NOW_X, y + NOW_DETAIL_Y)
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
                rgb = palette.EVENT.get(event.kind, palette.SECONDARY)
                alpha = 0.95 if event.major else 0.45
                colours += [(*rgb, alpha)] * 2
            if segments:
                self.marks.set_data(np.array(segments), color=np.array(colours))
            self._has_marks = bool(segments)
        # Outside the cache: the cold open's curtain hides this, and a visibility written
        # only when the event count changes would not come back until the next event.
        if self.marks.visible is not self._has_marks:
            self.marks.visible = self._has_marks

        px = self._px(t)
        self.playhead.set_data(np.array([[px, self.track_y - 18, 0.0],
                                         [px, self.track_y + 18, 0.0]]))

        left = max(0.0, T.MATCH_SECONDS - t)
        # Every one of these is gated on the integer second by `Slot.set`, which compares
        # before it assigns -- so the four strings here cost about one upload a second
        # between them rather than four a frame.
        self.clock.set(f"{int(t) // 60}:{int(t) % 60:02d}")
        self.clock_sub.set(f"of 8:00   -   {int(left) // 60}:{int(left) % 60:02d} left")
        event = feed.latest(t)
        self.now.set(event.text.upper() if event is not None else " ")
        self.now_detail.set(event.detail if event is not None and event.detail else " ")
