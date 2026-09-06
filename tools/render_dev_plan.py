"""Render docs/dev-plan.json into docs/DEV-PLAN.md, once.

The markdown is the board. Edit it by hand from then on -- tick the boxes, move the
status lines, add stories. The JSON is only how the first version was generated and
can be deleted once the markdown exists.

    python tools/render_dev_plan.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "dev-plan.json"
MD = ROOT / "docs" / "DEV-PLAN.md"

STATUSES: tuple[str, ...] = ("Backlog", "Ready", "In progress", "Blocked", "Done")


def load() -> dict[str, Any]:
    return json.loads(SRC.read_text(encoding="utf-8"))


def ordered_epics(plan: dict[str, Any]) -> list[dict[str, Any]]:
    by_key = {e["key"]: e for e in plan["epics"]}
    order = [k for k in plan.get("order_of_work", []) if k in by_key]
    rest = [e["key"] for e in plan["epics"] if e["key"] not in order]
    return [by_key[k] for k in order + rest]


def all_stories(plan: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [(e, s) for e in ordered_epics(plan) for s in e["stories"]]


def board(plan: dict[str, Any]) -> list[str]:
    """Ready = nothing to wait for. Everything else is blocked on a dependency or a gate."""
    lines = ["## Board\n",
             "Tick a story when it is done and move its `Status:` line. `Ready` means every "
             "dependency is done or there were none; the first epics in the order of work "
             "can start today.\n"]
    ready: list[str] = []
    blocked: list[str] = []
    for epic, s in all_stories(plan):
        entry = f"- [ ] **{s['key']}** {s['summary']} *({epic['key']}, {s['priority']}, {s.get('estimate_days', '?')}d)*"
        if s.get("depends_on"):
            blocked.append(entry + f" — after {', '.join(s['depends_on'])}")
        else:
            ready.append(entry)
    lines.append(f"### Ready now ({len(ready)})\n")
    lines += ready or ["- nothing"]
    lines.append("")
    lines.append(f"### Blocked on a dependency ({len(blocked)})\n")
    lines += blocked or ["- nothing"]
    lines.append("")
    lines.append("### In progress\n\n- (move stories here)\n")
    lines.append("### Done\n\n- (move stories here)\n")
    return lines


def write_md(plan: dict[str, Any]) -> None:
    totals = plan.get("totals", {})
    lines: list[str] = []
    lines.append("# Blindside — development plan\n")
    lines.append("This file is the board. Edit it directly. It was generated once from "
                 "`docs/dev-plan.json`; that file is disposable.\n")
    if totals:
        lines.append(f"**{totals.get('stories', '?')} stories · {totals.get('days', '?')} working days · "
                     f"~{totals.get('months_at_10_days_per_month', '?')} months at ten working days a month.** "
                     "Solo, nights and weekends. `DESIGN.html` calls 18–24 months to Phase 8 a floor; "
                     "treat any total under that as optimism.\n")

    lines.append("## Order of work\n")
    for i, epic in enumerate(ordered_epics(plan), 1):
        lines.append(f"{i}. **{epic['key']}** — {epic['title']} *(Phase {epic['phase']}, "
                     f"{epic.get('total_days', '?')} d)* — starts when: {epic['can_start_when']}")
    lines.append("")

    lines += board(plan)

    for epic in ordered_epics(plan):
        lines.append(f"## {epic['key']} — {epic['title']}\n")
        lines.append(f"**Phase {epic['phase']}.** {epic['goal']}\n")
        lines.append(f"- **Gate — pass:** {epic['gate_pass']}")
        lines.append(f"- **Gate — kill:** {epic['gate_kill']}")
        lines.append(f"- **Can start when:** {epic['can_start_when']}")
        lines.append(f"- **Estimate:** {epic.get('total_days', '?')} working days\n")
        lines.append("| Key | Type | Summary | Pri | Days | Depends on | Risk |")
        lines.append("|---|---|---|---|---|---|---|")
        for s in epic["stories"]:
            dep = ", ".join(s.get("depends_on", [])) or "—"
            lines.append(f"| {s['key']} | {s['type']} | {s['summary']} | {s['priority']} | "
                         f"{s.get('estimate_days', '')} | {dep} | {s.get('risk', '') or '—'} |")
        lines.append("")
        for s in epic["stories"]:
            lines.append(f"### {s['key']} — {s['summary']}\n")
            lines.append(f"**Status:** Backlog  ·  **{s['type']}**  ·  {s['priority']}  ·  "
                         f"{s.get('estimate_days', '?')} d"
                         + (f"  ·  depends on {', '.join(s['depends_on'])}" if s.get('depends_on') else "")
                         + (f"  ·  retires {s['risk']}" if s.get('risk') else "") + "\n")
            lines.append(s["description"] + "\n")
            if s.get("acceptance_criteria"):
                lines.append("Done when:")
                for a in s["acceptance_criteria"]:
                    lines.append(f"- [ ] {a}")
                lines.append("")

    verdicts = plan.get("reviewer_verdicts")
    if verdicts:
        lines.append("## Reviewer verdicts on this plan\n")
        for v in verdicts:
            lines.append(f"- {v}")
        lines.append("")
    MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    plan = load()
    write_md(plan)
    n = sum(len(e["stories"]) for e in plan["epics"])
    print(f"wrote {MD.relative_to(ROOT)}: {len(plan['epics'])} epics, {n} stories")


if __name__ == "__main__":
    main()
