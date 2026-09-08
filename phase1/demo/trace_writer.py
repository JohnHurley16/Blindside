"""Reads a match's decisions off as a Trace, and writes it as trace.json, per the contract."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..match.match_view import MatchView
from .run_outcome import RunOutcome
from .trace import Trace
from .trace_step import TraceStep


class TraceWriter:
    """Field names are the contract's and are final. `reason` is the one optional
    field this side adds (CAVE-BLOCKS.md 5)."""

    @staticmethod
    def from_match(match: MatchView, quit_at: float | None = None) -> Trace:
        """The player's recorded decisions, the run's blocks, and how it ended.

        Only stops at which the chosen action ran are steps: a no-op is not a
        demonstration (CAVE-BLOCKS.md 2.2, rule 2). `quit_at` is for a window closed
        before the end: the trace is written with what there is, marked lost, because
        eight minutes of a person's choices are worth more than a tidy outcome.
        """
        spec = match.spec
        steps = [TraceStep(tick=d.tick, junction=d.junction, predicates=dict(d.predicates),
                           raw=dict(d.raw), action=d.action, reason=d.reason)
                 for d in match.policies["player"].decisions if d.ran]
        result = match.result
        if result is not None:
            outcome = RunOutcome(success=result.extracted and result.cargo >= 1,
                                 ticks=result.ticks, lost=result.alive and not result.extracted,
                                 reason=result.why)
        elif quit_at is not None:
            outcome = RunOutcome(success=False, ticks=match.tick, lost=True,
                                 reason=f"quit at {int(quit_at) // 60}:{quit_at % 60:04.1f}")
        else:
            raise ValueError("the match is not over; a trace without an outcome is not finished")
        return Trace(seed=match.seed,
                     enabled_predicates=list(spec.enabled_predicates),
                     enabled_actions=list(spec.enabled_actions),
                     params={pid: dict(v) for pid, v in spec.params.items()
                             if pid in spec.enabled_predicates},
                     steps=steps, outcome=outcome)

    @staticmethod
    def to_json(trace: Trace) -> dict[str, Any]:
        if trace.outcome is None:
            raise ValueError("a trace without an outcome is not finished")
        return {
            "seed": trace.seed,
            "enabled_predicates": list(trace.enabled_predicates),
            "enabled_actions": list(trace.enabled_actions),
            "params": {pid: dict(vals) for pid, vals in trace.params.items()},
            "steps": [
                {
                    "tick": s.tick,
                    "junction": s.junction,
                    "predicates": dict(s.predicates),
                    "raw": dict(s.raw),
                    "action": s.action,
                    **({"reason": s.reason} if s.reason else {}),
                }
                for s in trace.steps
            ],
            "outcome": {
                "success": trace.outcome.success,
                "ticks": trace.outcome.ticks,
                "lost": trace.outcome.lost,
            },
        }

    @classmethod
    def write(cls, trace: Trace, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cls.to_json(trace), indent=1), encoding="utf-8")
        return path

    @staticmethod
    def read(path: Path) -> Trace:
        """A trace.json back into memory, for a replay."""
        data = json.loads(path.read_text(encoding="utf-8"))
        outcome = data["outcome"]
        return Trace(seed=int(data["seed"]),
                     enabled_predicates=list(data["enabled_predicates"]),
                     enabled_actions=list(data["enabled_actions"]),
                     params={pid: {k: float(v) for k, v in vals.items()}
                             for pid, vals in data["params"].items()},
                     steps=[TraceStep(tick=int(s["tick"]), junction=int(s["junction"]),
                                      predicates=dict(s["predicates"]),
                                      raw={k: float(v) for k, v in s["raw"].items()},
                                      action=str(s["action"]), reason=str(s.get("reason", "")))
                            for s in data["steps"]],
                     outcome=RunOutcome(success=bool(outcome["success"]), ticks=int(outcome["ticks"]),
                                        lost=bool(outcome["lost"])))
