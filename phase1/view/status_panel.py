"""Label-and-value rows. What the agent believes about itself, in plain words."""
from __future__ import annotations

from vispy.scene import visuals

from . import palette

ROW_HEIGHT: float = 30.0


class StatusPanel:
    def __init__(self, parent: object, x: float, y: float, width: float,
                 labels: tuple[str, ...]) -> None:
        self.x: float = x
        self.y: float = y
        self.width: float = width
        self.labels: tuple[str, ...] = labels
        self.label_visuals: list[object] = []
        self.value_visuals: list[object] = []
        self._cache: list[str] = [""] * len(labels)
        for index, label in enumerate(labels):
            row_y = y + index * ROW_HEIGHT
            self.label_visuals.append(
                visuals.Text(label, parent=parent, pos=(x + 12, row_y),
                             anchor_x="left", anchor_y="center",
                             color=palette.DIM, font_size=7.5))
            self.value_visuals.append(
                visuals.Text("", parent=parent, pos=(x + 12, row_y + 14),
                             anchor_x="left", anchor_y="center",
                             color=palette.TITLE, font_size=10.5, bold=True))

    def set(self, values: tuple[str, ...], colours: tuple[object, ...] | None = None) -> None:
        for index, value in enumerate(values):
            if index >= len(self.value_visuals):
                break
            if self._cache[index] != value:
                self._cache[index] = value
                self.value_visuals[index].text = value
            if colours is not None and colours[index] is not None:
                self.value_visuals[index].color = colours[index]

    @property
    def height(self) -> float:
        return len(self.labels) * ROW_HEIGHT
