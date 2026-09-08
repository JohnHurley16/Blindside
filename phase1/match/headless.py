"""Run a match with no display and print a merged belief/truth timeline.

For tuning only. The truth lines in this output are the reason it exists -- they are
what tells you whether the drift is large enough to see -- and they never reach the
renderer.
"""
from __future__ import annotations

import math
from pathlib import Path

from .. import tuning as T
from .sim import Sim

TimelineEntry = tuple[float, str, str]


def format_time(t: float) -> str:
    return f"{int(t) // 60}:{t % 60:04.1f}"


def run_headless(recall_at: float | None = None, seed: int = T.SEED,
                 report_every: float = 30.0, quiet: bool = False,
                 tree: Path | None = None) -> Sim:
    sim = Sim(seed, tree=tree)
    timeline: list[TimelineEntry] = []
    seen: dict[str, int] = {name: 0 for name in sim.beliefs}
    next_report = 0.0

    while not sim.over:
        if recall_at is not None and sim.t >= recall_at and not sim.recall_used:
            sim.recall()
        sim.step()
        if sim.tick % 10 == 0:
            sim.record_truth_trail()
        if sim.t >= next_report:
            next_report += report_every
            for name, agent in sim._world.agents.items():
                b = sim.beliefs[name]
                err = math.hypot(agent.x - b.x, agent.y - b.y)
                herr = math.degrees((b.theta - agent.heading + math.pi) % (2 * math.pi) - math.pi)
                timeline.append((sim.t, name,
                                 f"[truth] pos err {err:5.1f} hdg err {herr:6.1f} "
                                 f"sigma {b.sigma_pos():5.1f} "
                                 f"truth ({agent.x:3.0f},{agent.y:3.0f}) "
                                 f"belief ({b.x:3.0f},{b.y:3.0f}) "
                                 f"{sim.policies[name].doing} pts {b.cloud.n}"))
        for name, belief in sim.beliefs.items():
            for entry in belief.log[seen[name]:]:
                timeline.append((entry[0], name, entry[1]))
            seen[name] = len(belief.log)

    for event in sim._world.events:
        timeline.append((event.t, "TRUTH", str(event)))
    timeline.sort(key=lambda e: e[0])

    if not quiet:
        for t, who, text in timeline:
            print(f"{format_time(t)} {who:6s} {text}")
        print("RESULT", sim.result)
    sim.timeline = timeline    # type: ignore[attr-defined]
    return sim
