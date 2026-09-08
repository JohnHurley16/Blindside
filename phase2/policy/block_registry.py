"""The block list, loaded from blocks.json, joined to its implementations.

**This is the one place in Python where block ids appear.** Everything else --
the tree interpreter, the session, the demonstration, the evaluator -- works over
the list this exposes, so that adding a block is a data change plus one entry here.
A parametric block's provisional threshold is data on the list too, beside the block.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Mapping

from ..belief.belief import Belief
from ..motor import return_to_beacon, take_branch
from ..motor.motor_command import MotorCommand
from .action import Action
from .predicate import Predicate
from .predicates import carrying_cargo, uncertainty_exceeds, unexplored_branch_exists

BLOCKS_PATH: Path = Path(__file__).resolve().parent.parent / "blocks.json"

Evaluator = Callable[[Belief, Mapping[str, float]], tuple[bool, float | None]]
Motor = Callable[[Belief], MotorCommand]


class BlockRegistry:
    """Predicates and actions keyed by stable id."""

    def __init__(self, path: Path = BLOCKS_PATH) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        self.path: Path = path
        self.predicates: list[Predicate] = [
            Predicate(id=p["id"], label=p["label"], param=p.get("param"), stage=int(p.get("stage", 1)))
            for p in data["predicates"]
        ]
        self.actions: list[Action] = [
            Action(id=a["id"], label=a["label"], stage=int(a.get("stage", 1)))
            for a in data["actions"]
        ]
        # The provisional threshold beside each parametric predicate on the list: what a
        # demonstration reads its boolean with until the induction fits the real one.
        # crates/blindside-induct/FORMAT.md says why it lives on the list and why it sits low.
        self._provisional: dict[str, float] = {
            p["id"]: float(p["provisional"]) for p in data["predicates"] if "provisional" in p}
        stray = [p.id for p in self.predicates if p.param is None and p.id in self._provisional]
        if stray:
            raise ValueError(f"blocks in {path.name} with a provisional value but no param: {stray}")
        unset = [p for p in self.predicates if p.param is not None and p.id not in self._provisional]
        if unset:
            raise ValueError("; ".join(
                f"{p.id} takes a parameter named {p.param!r} and {path.name} gives it no "
                f"provisional value" for p in unset))
        self._evaluators: dict[str, Evaluator] = {
            "unexplored_branch_exists": unexplored_branch_exists.evaluate,
            "uncertainty_exceeds": uncertainty_exceeds.evaluate,
            "carrying_cargo": carrying_cargo.evaluate,
        }
        self._motors: dict[str, Motor] = {
            "take_branch": take_branch.plan,
            "return_to_beacon": return_to_beacon.plan,
        }
        missing = [p.id for p in self.predicates if p.id not in self._evaluators]
        missing += [a.id for a in self.actions if a.id not in self._motors]
        if missing:
            raise ValueError(f"blocks listed in {path.name} with no implementation: {missing}")
        self._by_id: dict[str, Predicate] = {p.id: p for p in self.predicates}
        self._action_by_id: dict[str, Action] = {a.id: a for a in self.actions}

    # ---- the list ----------------------------------------------------------------------
    def predicate_ids(self) -> list[str]:
        return [p.id for p in self.predicates]

    def action_ids(self) -> list[str]:
        return [a.id for a in self.actions]

    def predicate(self, predicate_id: str) -> Predicate:
        return self._by_id[predicate_id]

    def action(self, action_id: str) -> Action:
        return self._action_by_id[action_id]

    def predicate_ids_by_stage(self, stage: int) -> list[str]:
        """The predicates that exist by the given tutorial run."""
        return [p.id for p in self.predicates if p.stage <= stage]

    def action_ids_by_stage(self, stage: int) -> list[str]:
        return [a.id for a in self.actions if a.stage <= stage]

    def last_stage(self) -> int:
        return max([p.stage for p in self.predicates] + [a.stage for a in self.actions])

    def parametric_ids(self) -> list[str]:
        return [p.id for p in self.predicates if p.param is not None]

    def provisional_params(self, predicate_ids: list[str] | None = None) -> dict[str, dict[str, float]]:
        """The value each parametric predicate's boolean is read with in a demonstration:
        the `provisional` beside it on the block list, by the parameter's name. Every
        parametric predicate on the list has one (checked at load), or a run that enables
        it would have no boolean to show. The value is provisional and the panel says so:
        the induction refits it."""
        out: dict[str, dict[str, float]] = {}
        for p in self.predicates:
            if predicate_ids is not None and p.id not in predicate_ids:
                continue
            if p.param is None:
                continue
            out[p.id] = {p.param: self._provisional[p.id]}
        return out

    # ---- the implementations -------------------------------------------------------------
    def evaluators(self) -> dict[str, Evaluator]:
        """id -> (belief, params) -> (bool, raw | None), for every listed predicate."""
        return {p.id: self._evaluators[p.id] for p in self.predicates}

    def evaluate(self, predicate_id: str, belief: Belief,
                 params: Mapping[str, float]) -> tuple[bool, float | None]:
        return self._evaluators[predicate_id](belief, params)

    def motor(self, action_id: str) -> Motor:
        return self._motors[action_id]
