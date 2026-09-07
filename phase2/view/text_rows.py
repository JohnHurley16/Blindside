"""A column of text lines with a fixed pool of visuals.

Phase 1's lesson, kept: a `Text` visual rebuilds a glyph atlas when its string
changes, so every panel here writes through this and every write is compared with
what is already there. The pool is allocated once at construction; a redraw only
moves the cursor and, at most, sets the strings that actually differ.
"""
from __future__ import annotations

import textwrap

from vispy.scene import visuals

from . import palette

Rgb = tuple[float, float, float]


class TextRows:
    """`begin`, then a `line` per row, then `end`. Rows past the last are hidden."""

    def __init__(self, parent: object, x: float, y: float, width: float,
                 capacity: int = 48, line_height: float = 14.0,
                 font_size: float = 8.0) -> None:
        self.x: float = x
        self.y: float = y
        self.width: float = width
        self.line_height: float = line_height
        self.cursor: float = y
        self.used: int = 0
        self._text: list[str] = [""] * capacity
        self._pos: list[tuple[float, float]] = [(0.0, 0.0)] * capacity
        self._colour: list[Rgb] = [palette.DIM] * capacity
        self._size: list[float] = [font_size] * capacity
        self.rows: list[object] = [
            visuals.Text("", parent=parent, pos=(x, y), anchor_x="left", anchor_y="center",
                         color=palette.DIM, font_size=font_size)
            for _ in range(capacity)
        ]
        for row in self.rows:
            row.visible = False        # type: ignore[attr-defined]

    # ---- writing ------------------------------------------------------------------------
    def begin(self) -> None:
        self.cursor = self.y
        self.used = 0

    def line(self, text: str, colour: Rgb = palette.DIM, size: float = 8.0,
             indent: float = 0.0, gap: float = 0.0) -> None:
        self.cursor += gap
        if self.used >= len(self.rows):
            return
        index = self.used
        row = self.rows[index]
        if self._text[index] != text:
            self._text[index] = text
            row.text = text            # type: ignore[attr-defined]
        position = (self.x + indent, self.cursor)
        if self._pos[index] != position:
            self._pos[index] = position
            row.pos = position         # type: ignore[attr-defined]
        if self._colour[index] != colour:
            self._colour[index] = colour
            row.color = colour         # type: ignore[attr-defined]
        if self._size[index] != size:
            self._size[index] = size
            row.font_size = size       # type: ignore[attr-defined]
        row.visible = True             # type: ignore[attr-defined]
        self.used += 1
        self.cursor += self.line_height

    def chars(self, size: float) -> int:
        """How many characters of this size fit across the column.

        Measured off a render rather than guessed: at font_size s a character of
        this face is about s logical pixels wide, so the budget is the width over
        the size. Getting this wrong is what runs a label off the edge of a panel.
        """
        return max(10, int(self.width / max(size, 1.0)))

    def wrapped(self, text: str, colour: Rgb = palette.DIM, size: float = 8.0,
                indent: float = 0.0, gap: float = 0.0) -> None:
        for offset, part in enumerate(textwrap.wrap(text, self.chars(size)) or [""]):
            self.line(part, colour, size, indent, gap if offset == 0 else 0.0)

    def hanging(self, text: str, colour: Rgb = palette.DIM, size: float = 8.0,
                gap: float = 0.0, step: float = 6.0) -> None:
        """A line whose own leading spaces are its indent, wrapped under itself.

        The rendered tree's indentation is what makes it a tree; wrapping a long
        label has to keep it.
        """
        stripped = text.lstrip(" ")
        depth = len(text) - len(stripped)
        indent = depth * step
        budget = max(8, self.chars(size) - depth)
        for offset, part in enumerate(textwrap.wrap(stripped, budget) or [""]):
            self.line(part, colour, size, indent + (0.0 if offset == 0 else step * 2),
                      gap if offset == 0 else 0.0)

    def end(self) -> None:
        for row in self.rows[self.used:]:
            row.visible = False        # type: ignore[attr-defined]

    def move(self, x: float, y: float, width: float | None = None) -> None:
        self.x, self.y = x, y
        if width is not None:
            self.width = width
