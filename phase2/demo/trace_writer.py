"""Writes a Trace as trace.json, exactly per the contract."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .trace import Trace


class TraceWriter:
    """Field names are the contract's and are final."""

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
