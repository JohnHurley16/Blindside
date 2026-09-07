"""The induced rule: the tree as lines, and the tree as one sentence.

Both strings come from `induct render`, so the words a player reads are the block
list's labels arranged by the induction. This file does not build them and does not
know a block id.

During a ghost replay the lines on the path a stop took are lit, and the stop where
the tree first chose differently from the demonstration is flagged. Which lines
those are is worked out by `tree_path`, which walks the tree in the same order the
render prints it.
"""
from __future__ import annotations

from typing import Iterable, Sequence

from ..seam.rendered import Rendered
from . import palette
from .text_rows import TextRows

HEADING_SIZE: float = 7.5
TREE_SIZE: float = 8.0
PROSE_SIZE: float = 8.5


class TreePanel:
    """Nothing but drawing: what to light is decided outside and handed in."""

    def __init__(self, parent: object, x: float, y: float, width: float) -> None:
        self.rows: TextRows = TextRows(parent, x + 16, y + 18, width - 32,
                                       capacity=72, line_height=15.0)

    def move(self, x: float, y: float, width: float) -> None:
        self.rows.move(x + 16, y + 18, width - 32)

    def update(self, rendered: Rendered | None, lit: Iterable[int], flagged: bool,
               notes: Sequence[str]) -> None:
        lit_set = set(lit)
        rows = self.rows
        rows.begin()
        rows.line("THE RULE IT LEARNED", palette.DIM, HEADING_SIZE)
        if rendered is None:
            rows.wrapped("nothing yet: it is induced from every run, once they are all "
                         "done", palette.DIM, PROSE_SIZE, gap=10.0)
            rows.end()
            return
        for index, line in enumerate(rendered.lines):
            on = index in lit_set
            colour = palette.TREE_FLAG if (on and flagged) else (
                palette.TREE_LIVE if on else palette.TREE_IDLE)
            rows.hanging(line, colour, TREE_SIZE, gap=8.0 if index == 0 else 0.0)
        rows.line("IN WORDS", palette.DIM, HEADING_SIZE, gap=20.0)
        rows.wrapped(rendered.sentence, palette.TITLE, PROSE_SIZE, gap=8.0)
        for note in notes:
            rows.wrapped(note, palette.BANNER if flagged else palette.HUD, PROSE_SIZE,
                         gap=12.0)
        rows.end()
