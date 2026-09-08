"""The blocks that exist in this run, at the stop the machine is waiting on.

The corridor's block panel (`phase2/view/block_panel.py`), written over the shared
text group. Every word in here comes from the block list: the labels of the
predicates that exist, the name of the parameter a parametric one carries, and the
labels of the actions the number keys are bound to. This file names no block.

A parametric predicate is shown twice over: the boolean, which needs a value of its
parameter to exist at all, and the raw number the boolean was read from. The value
is provisional and the panel says so, because the induction refits the threshold
from the raw numbers in the trace and ignores the boolean entirely.

Between stops the panel keeps reading the same predicates off Belief, at
TEACH_VALUES_HZ, so a number can be watched creeping toward the threshold that will
stop the machine. At a stop it shows the stop's own values -- the ones the trace
records -- and the actions that would do something here are the ones offered; a
no-op is greyed and its key refused, because a stop where nothing happened is not
a demonstration and could not be replayed.
"""
from __future__ import annotations

import textwrap

from .. import tuning as T
from ..belief.belief import Belief
from ..policy.block_registry import BlockRegistry
from ..policy.run_spec import RunSpec
from ..policy.stop_view import StopView
from . import palette
from .text_group import BODY, HEAD, MICRO, Slot, TextGroup

TITLE: str = "WHAT IT BELIEVES HERE"
ACTIONS: str = "WHAT YOU CAN DO"
LABEL_LINES: int = 2               # a label may wrap onto this many rows
ACTION_LINES: int = 2
ROW_H: float = 17.0                # px per wrapped row of body text
VALUE_DROP: float = 20.0           # px from the last label row down to the value
PREDICATE_GAP: float = 12.0        # px after a predicate's value, before the next label
TITLE_H: float = 24.0
ACTIONS_GAP: float = 22.0
WRAP_PX_PER_CHAR: float = 9.5      # 11 pt of this face: measured off a rail render at the
                                   # recorder's 1.25x DPI, where 30 characters filled the rail


class BlockPanel:
    """Predicates with their values, then the actions offered as numbered choices."""

    def __init__(self, group: TextGroup, registry: BlockRegistry, spec: RunSpec) -> None:
        self.registry: BlockRegistry = registry
        self.spec: RunSpec = spec
        self.x: float = 0.0
        self.y: float = 0.0
        self.width: float = T.RAIL_W - 2.0 * T.MARGIN
        chars = max(12, int(self.width / WRAP_PX_PER_CHAR))
        self.title: Slot = group.slot(BODY, TITLE, rgb=palette.SECONDARY)
        self.labels: dict[str, list[Slot]] = {}
        self.provisional: dict[str, Slot] = {}
        self.values: dict[str, Slot] = {}
        self.label_rows: dict[str, int] = {}
        for pid in spec.enabled_predicates:
            block = registry.predicate(pid)
            rows = (textwrap.wrap(block.label, chars) or [""])[:LABEL_LINES]
            self.label_rows[pid] = len(rows)
            self.labels[pid] = [group.slot(BODY, text, rgb=palette.SECONDARY) for text in rows]
            if block.param is not None:
                setting = spec.params.get(pid, {}).get(block.param)
                # Provisional, and the panel says so: the induction refits it.
                text = (f"{block.param} = {setting:g}  (provisional)"
                        if setting is not None else f"{block.param}: no value")
                self.provisional[pid] = group.slot(MICRO, text, rgb=palette.TERTIARY)
            self.values[pid] = group.slot(HEAD, "-", rgb=palette.TERTIARY)
        self.actions_title: Slot = group.slot(BODY, ACTIONS, rgb=palette.SECONDARY)
        self.action_slots: dict[str, list[Slot]] = {}
        self.action_rows: dict[str, list[str]] = {}          # offered
        self.action_rows_off: dict[str, list[str]] = {}      # a no-op here
        for index, aid in enumerate(spec.enabled_actions):
            label = f"[{index + 1}]   {registry.action(aid).label}"
            rows = (textwrap.wrap(label, chars) or [""])[:ACTION_LINES]
            off = (textwrap.wrap(f"{label} - nothing to do here", chars) or [""])[:ACTION_LINES]
            self.action_rows[aid] = rows + [" "] * (ACTION_LINES - len(rows))
            self.action_rows_off[aid] = off + [" "] * (ACTION_LINES - len(off))
            self.action_slots[aid] = [group.slot(BODY, text, rgb=palette.TERTIARY)
                                      for text in self.action_rows[aid]]
        self._last_live_t: float = -1e9

    # ---- geometry -----------------------------------------------------------------------
    def move(self, x: float, y: float) -> None:
        self.x, self.y = x, y
        self.title.at(x, y)
        cursor = y + TITLE_H
        for pid in self.spec.enabled_predicates:
            for slot in self.labels[pid]:
                slot.at(x, cursor)
                cursor += ROW_H
            if pid in self.provisional:
                self.provisional[pid].at(x + 12.0, cursor - 2.0)
                cursor += ROW_H - 3.0
            self.values[pid].at(x + 12.0, cursor + VALUE_DROP - ROW_H + 6.0)
            cursor += VALUE_DROP + PREDICATE_GAP
        cursor += ACTIONS_GAP - PREDICATE_GAP
        self.actions_title.at(x, cursor)
        cursor += TITLE_H
        for aid in self.spec.enabled_actions:
            for index, slot in enumerate(self.action_slots[aid]):
                slot.at(x + (0.0 if index == 0 else 30.0), cursor)
                cursor += ROW_H
            cursor += 4.0
        self._bottom = cursor

    @property
    def height(self) -> float:
        return self._bottom - self.y

    # ---- one frame -------------------------------------------------------------------------
    def update(self, stop: StopView | None, belief: Belief, t: float) -> None:
        """At a stop, the stop's values and the offered keys; between stops, the live
        values at TEACH_VALUES_HZ and every key dimmed."""
        if stop is not None:
            self._values(stop.predicates, stop.raw)
            for aid in self.spec.enabled_actions:
                offered = stop.available.get(aid, True)
                rows = self.action_rows[aid] if offered else self.action_rows_off[aid]
                for index, slot in enumerate(self.action_slots[aid]):
                    slot.set(rows[index])
                    slot.tint(palette.PRIMARY if offered else palette.TERTIARY)
            self.title.tint(palette.PRIMARY)
            self._last_live_t = -1e9
            return
        self.title.set(TITLE)
        self.title.tint(palette.SECONDARY)
        for aid in self.spec.enabled_actions:
            for index, slot in enumerate(self.action_slots[aid]):
                slot.set(self.action_rows[aid][index])
                slot.tint(palette.TERTIARY)
        if t - self._last_live_t < 1.0 / T.TEACH_VALUES_HZ:
            return
        self._last_live_t = t
        predicates: dict[str, bool] = {}
        raw: dict[str, float] = {}
        for pid in self.spec.enabled_predicates:
            value, number = self.registry.evaluate(pid, belief, self.spec.params.get(pid, {}))
            predicates[pid] = value
            if number is not None:
                raw[pid] = number
        self._values(predicates, raw)

    def _values(self, predicates: dict[str, bool], raw: dict[str, float]) -> None:
        for pid in self.spec.enabled_predicates:
            value = predicates.get(pid)
            text = "-" if value is None else ("yes" if value else "no")
            number = raw.get(pid)
            if number is not None:
                text = f"{text}        {number:.1f}"
            self.values[pid].set(text)
            self.values[pid].tint(palette.PRIMARY if value else palette.SECONDARY)
