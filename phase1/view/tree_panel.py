"""The rule the machine is running, on the spectator rail, lit along the path it took.

Both strings come from `induct render` (`TaughtRule`), so the words a viewer reads
are the block list's labels arranged by the induction. This file does not build
them and does not know a block id. It is the corridor's tree panel written over the
shared text group: every string is a fixed slot registered at construction, and a
frame changes colours only -- the lit path moves, the words never do -- because a
changed string re-uploads a whole group and this panel sits in the group with most
of the rail's words in it.

The lines on the path the last decision walked are lit; the leaf it reached is the
action running under the panel. Between decisions nothing changes, which is right:
the machine decided, and this is what it decided by.
"""
from __future__ import annotations

import textwrap

from .. import tuning as T
from . import palette
from .taught_rule import TaughtRule
from .text_group import BODY, MICRO, Slot, TextGroup

TITLE: str = "THE RULE IT WAS TAUGHT"
WORDS: str = "IN WORDS"
TITLE_H: float = 20.0            # px from a heading to its first line
WORDS_GAP: float = 10.0          # px between the tree and the IN WORDS heading
INDENT_PX: float = 5.0           # px per leading space of a rendered line (two per level)
WRAP_PX_PER_CHAR: float = 7.8    # 9 pt of this face: measured off a rail render at 1.25x DPI
LINE_ROWS: int = 2               # a rendered line may wrap onto this many rows, hanging
HANG_PX: float = 12.0            # the hanging indent of a wrapped line's second row


class TreePanel:
    """Fixed slots, moved by `move`, coloured by `update`."""

    def __init__(self, group: TextGroup, rule: TaughtRule) -> None:
        self.rule: TaughtRule = rule
        self.x: float = 0.0
        self.y: float = 0.0
        self.width: float = T.RAIL_W - 2.0 * T.MARGIN
        self.title: Slot = group.slot(BODY, TITLE, rgb=palette.SECONDARY)
        self.lines: list[str] = list(rule.lines[:T.TEACH_TREE_MAX_LINES])
        # A line keeps its indentation -- that is what makes it a tree -- and a long one
        # wraps under itself, as the corridor's panel wrapped it.
        self.line_rows: list[list[str]] = []
        self.line_slots: list[list[Slot]] = []
        for text in self.lines:
            depth = len(text) - len(text.lstrip(" "))
            budget = max(8, int((self.width - depth * INDENT_PX) / WRAP_PX_PER_CHAR))
            rows = (textwrap.wrap(text.lstrip(" "), budget) or [""])[:LINE_ROWS]
            self.line_rows.append(rows)
            self.line_slots.append([group.slot(MICRO, row, rgb=palette.TERTIARY) for row in rows])
        self.more: Slot | None = None
        if len(rule.lines) > len(self.lines):
            self.more = group.slot(MICRO, f"... and {len(rule.lines) - len(self.lines)} more lines",
                                   rgb=palette.TERTIARY)
        self.words: Slot = group.slot(BODY, WORDS, rgb=palette.SECONDARY)
        chars = max(12, int(self.width / WRAP_PX_PER_CHAR))
        self.sentence: list[str] = textwrap.wrap(rule.sentence, chars) or [""]
        self.sentence_slots: list[Slot] = [
            group.slot(MICRO, part, rgb=palette.PRIMARY) for part in self.sentence]
        self._lit: tuple[int, ...] = ()
        self._shown_words: bool = True

    # ---- geometry -----------------------------------------------------------------------
    def move(self, x: float, y: float, bottom: float) -> None:
        """Lay the panel out between `y` and `bottom`; what does not fit is hidden
        rather than printed on whatever is below."""
        self.x, self.y = x, y
        pitch = T.TEACH_TREE_LINE_H
        self.title.at(x, y)
        cursor = y + TITLE_H
        for text, slots in zip(self.lines, self.line_slots):
            depth = len(text) - len(text.lstrip(" "))
            for row, slot in enumerate(slots):
                slot.at(x + depth * INDENT_PX + (HANG_PX if row else 0.0), cursor)
                cursor += pitch
        if self.more is not None:
            self.more.at(x, cursor)
            cursor += pitch
        # The sentence is never the thing that gets dropped. It is the plain-English form of
        # the rule and it is what PROTOCOL.md puts in front of a tester; the tree above it is
        # a diagram of the same thing. Before this was reversed (2026-09-10, found while
        # capturing this window for the trailer) a player at the default window size had
        # never once seen it, because `move` hid it whenever the space below the tree was
        # short, and at the default size it always was.
        need = WORDS_GAP + TITLE_H + pitch * len(self.sentence)
        self._shown_words = True
        over = (cursor + need) - bottom
        if over > 0.0:
            # Hide tree lines from the bottom until the sentence fits, and say how many.
            drop = int(over // pitch) + 1
            shown = 0
            for text, slots in zip(self.lines, self.line_slots):
                shown += len(slots)
            keep = max(1, shown - drop)
            seen = 0
            for text, slots in zip(self.lines, self.line_slots):
                for slot in slots:
                    seen += 1
                    if seen > keep:
                        slot.set(" ")
            cursor -= pitch * min(drop, shown - 1)
            if self.more is not None:
                self.more.at(x, cursor)
                cursor += pitch
        cursor += WORDS_GAP
        self.words.at(x, cursor)
        cursor += TITLE_H
        for slot in self.sentence_slots:
            slot.at(x, cursor)
            cursor += pitch
        self.words.set(WORDS)
        for part, slot in zip(self.sentence, self.sentence_slots):
            slot.set(part)

    # ---- one frame -------------------------------------------------------------------------
    def update(self, lit: list[int], recalled: bool) -> None:
        """Light the lines on the last decision's path. Cached on the path, so a frame
        with the same decision standing costs nothing."""
        key = tuple(sorted(lit)) if not recalled else (-1,)
        if key == self._lit:
            return
        self._lit = key
        on = set(lit) if not recalled else set()
        for index, slots in enumerate(self.line_slots):
            for slot in slots:
                slot.tint(palette.PRIMARY if index in on else palette.TERTIARY)
        self.title.set("THE RULE IT WAS TAUGHT - OVERRIDDEN BY RECALL" if recalled else TITLE)

    @property
    def height(self) -> float:
        lines = sum(len(rows) for rows in self.line_rows) + (1 if self.more is not None else 0)
        tree = TITLE_H + T.TEACH_TREE_LINE_H * lines
        if not self._shown_words:
            return tree
        return tree + WORDS_GAP + TITLE_H + T.TEACH_TREE_LINE_H * len(self.sentence)
