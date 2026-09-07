"""A tiny validator for trace.json against blocks.json.

    python -m phase2.demo.trace_validator --blocks phase2/blocks.json TRACE.json [...]

Checks shape and the contract's rules: enabled ids come from the block list,
every step carries exactly the enabled predicates and a raw number for each
enabled parametric one, every action is enabled, params cover the enabled
parametric predicates. Names no block.

`params` is the one map that may say more than the run used. The contract's rule
that a disabled predicate is "absent from both maps" is written about a step's
`predicates` and `raw`; the contract's own trace.json example then carries a
`params` entry for a predicate that is not enabled. The writer here filters
`params` to the enabled predicates -- a demonstration should record the numbers
it actually ran with -- but a trace that carries a spare entry is accepted, so
the two sides of the seam cannot disagree about it. Anything named in `params`
must still be a predicate on the block list.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def validate(trace: dict[str, Any], blocks: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    predicate_ids = {p["id"] for p in blocks["predicates"]}
    action_ids = {a["id"] for a in blocks["actions"]}
    param_of = {p["id"]: p.get("param") for p in blocks["predicates"]}

    for key in ("seed", "enabled_predicates", "enabled_actions", "params", "steps", "outcome"):
        if key not in trace:
            problems.append(f"missing top-level field {key!r}")
    if problems:
        return problems
    if not isinstance(trace["seed"], int):
        problems.append("seed is not an integer")
    enabled_p = trace["enabled_predicates"]
    enabled_a = trace["enabled_actions"]
    for pid in enabled_p:
        if pid not in predicate_ids:
            problems.append(f"enabled predicate not in the block list: {pid}")
    for aid in enabled_a:
        if aid not in action_ids:
            problems.append(f"enabled action not in the block list: {aid}")
    parametric = [pid for pid in enabled_p if param_of.get(pid)]
    for pid in parametric:
        if param_of[pid] not in trace["params"].get(pid, {}):
            problems.append(f"params lacks {param_of[pid]} for enabled predicate {pid}")
    for pid in trace["params"]:
        # Deliberately not "not enabled": see the note at the head of this module.
        if pid not in predicate_ids:
            problems.append(f"params names a predicate not in the block list: {pid}")

    last_tick = -1
    for i, step in enumerate(trace["steps"]):
        where = f"step {i}"
        for key in ("tick", "junction", "predicates", "raw", "action"):
            if key not in step:
                problems.append(f"{where}: missing {key!r}")
        if any(k not in step for k in ("tick", "junction", "predicates", "raw", "action")):
            continue
        if not isinstance(step["tick"], int) or step["tick"] < last_tick:
            problems.append(f"{where}: tick {step['tick']!r} is not a non-decreasing integer")
        last_tick = step["tick"] if isinstance(step["tick"], int) else last_tick
        if not isinstance(step["junction"], int):
            problems.append(f"{where}: junction is not an integer")
        if set(step["predicates"]) != set(enabled_p):
            problems.append(f"{where}: predicates {sorted(step['predicates'])} != enabled {sorted(enabled_p)}")
        for pid, value in step["predicates"].items():
            if not isinstance(value, bool):
                problems.append(f"{where}: predicate {pid} is not a boolean")
        if set(step["raw"]) != set(parametric):
            problems.append(f"{where}: raw {sorted(step['raw'])} != enabled parametric {sorted(parametric)}")
        for pid, number in step["raw"].items():
            if isinstance(number, bool) or not isinstance(number, (int, float)):
                problems.append(f"{where}: raw {pid} is not a number")
        if step["action"] not in enabled_a:
            problems.append(f"{where}: action {step['action']!r} is not enabled")

    outcome = trace["outcome"]
    for key, kind in (("success", bool), ("ticks", int), ("lost", bool)):
        if key not in outcome or not isinstance(outcome[key], kind):
            problems.append(f"outcome.{key} missing or not {kind.__name__}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="phase2.demo.trace_validator")
    parser.add_argument("--blocks", type=Path, required=True)
    parser.add_argument("traces", type=Path, nargs="+")
    args = parser.parse_args(argv)
    blocks = json.loads(args.blocks.read_text(encoding="utf-8"))
    bad = 0
    for path in args.traces:
        trace = json.loads(path.read_text(encoding="utf-8"))
        problems = validate(trace, blocks)
        steps = len(trace.get("steps", []))
        if problems:
            bad += 1
            print(f"{path}: INVALID")
            for p in problems:
                print(f"  {p}")
        else:
            outcome = trace["outcome"]
            print(f"{path}: valid, {steps} steps, seed {trace['seed']}, "
                  f"success={outcome['success']} lost={outcome['lost']} ticks={outcome['ticks']}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
