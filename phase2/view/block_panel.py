"""The blocks that exist in this run, at the stop the run is waiting on.

Every word in here comes from the block list: the labels of the predicates that
exist, the label of the parameter a parametric one carries, and the labels of the
actions the number keys are bound to. This file names no block.

A parametric predicate is shown twice over: the boolean, which needs a value of its
parameter to exist at all, and the raw number the boolean was read from. The value
is provisional and the panel says so, because the induction refits the threshold
from the raw numbers in the trace and ignores the boolean entirely.
"""
from __future__ import annotations

from typing import Mapping, Sequence

from ..demo.stop_view import StopView
from ..policy.block_registry import BlockRegistry
from . import palette
from .text_rows import TextRows

LABEL_SIZE: float = 8.5
VALUE_SIZE: float = 10.0
SMALL_SIZE: float = 7.0
HEADING_SIZE: float = 7.5


class BlockPanel:
    """Predicates with their values, then the actions offered as numbered choices."""

    def __init__(self, parent: object, x: float, y: float, width: float,
                 registry: BlockRegistry) -> None:
        self.registry: BlockRegistry = registry
        capacity = 8 + 6 * (len(registry.predicates) + len(registry.actions))
        self.rows: TextRows = TextRows(parent, x + 16, y + 18, width - 32,
                                       capacity=capacity, line_height=16.0)

    def move(self, x: float, y: float, width: float) -> None:
        self.rows.move(x + 16, y + 18, width - 32)

    def update(self, stop: StopView | None, predicates: Sequence[str],
               actions: Sequence[str], params: Mapping[str, Mapping[str, float]],
               waiting: bool) -> None:
        rows = self.rows
        rows.begin()
        rows.line("WHAT IT BELIEVES HERE", palette.DIM, HEADING_SIZE)
        if stop is None:
            rows.wrapped("the agent is between junctions", palette.DIM, LABEL_SIZE, gap=10.0)
        else:
            for pid in predicates:
                block = self.registry.predicate(pid)
                value = stop.predicates.get(pid)
                rows.wrapped(block.label, palette.HUD, LABEL_SIZE, gap=12.0)
                if block.param is not None:
                    setting = params.get(pid, {}).get(block.param)
                    if setting is not None:
                        rows.wrapped(f"{block.param} = {setting:g}, provisional - the rule "
                                     f"refits it", palette.DIM, SMALL_SIZE, indent=12.0)
                text = "-" if value is None else ("yes" if value else "no")
                raw = stop.raw.get(pid)
                if raw is not None:
                    text = f"{text}        {raw:.1f}"
                rows.line(text, palette.YES if value else palette.NO, VALUE_SIZE, indent=12.0)
        rows.line("WHAT YOU CAN DO", palette.DIM, HEADING_SIZE, gap=20.0)
        for index, action in enumerate(actions):
            rows.wrapped(f"[{index + 1}]   {self.registry.action(action).label}",
                         palette.KEY if waiting else palette.DIM, 9.5, gap=6.0)
        rows.end()
