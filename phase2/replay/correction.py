"""Scrub to a stop, take over from there, promote what you did, induce again.

`PHASE-2-OPEN-QUESTIONS.md` (f) is the rule this file implements: a correction
means *the rule I taught was wrong from here*, so the promoted demonstration is
the original trace up to the scrub point plus the new choices after it --
**replaced, not appended**. Appending would leave the wrong choice in the evidence
and fire the contradiction query on the player's own mistake.

The re-simulation is exact rather than approximate: the same seed opens the same
corridor and the same drift stream, and replaying the recorded choices reproduces
the recorded stops. `scrub` checks that, stop by stop, and refuses if it does not.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from ..demo.recording import Recording
from ..demo.run_source import RunSource
from ..demo.trace import Trace
from ..demo.trace_step import TraceStep
from ..demo.trace_writer import TraceWriter
from ..eval.run_outcome import RunOutcome
from ..induct_client import InductClient
from ..seam.induction import Induction
from .takeover import Takeover


def scrub(source: RunSource, recording: Recording, index: int) -> Takeover:
    """Re-simulate the run to stop `index` and hand it to a chooser.

    Every stop before `index` replays the choice the demonstration recorded there;
    the stop and junction it lands on must be the ones the trace wrote down, or the
    replay is not the same run and the correction would be about a different one.
    """
    trace = recording.trace
    if not 0 <= index < len(trace.steps):
        raise IndexError(f"stop {index} is outside the {len(trace.steps)} the run has")
    driver = source.open(trace.seed,
                         enabled_predicates=trace.enabled_predicates,
                         enabled_actions=trace.enabled_actions,
                         params=trace.params, drift=recording.stage.drift)
    for step in trace.steps[:index]:
        view = driver.advance_to_stop()
        if view is None:
            raise RuntimeError(f"the replay of seed {trace.seed} ended before stop {index}")
        if (view.tick, view.junction) != (step.tick, step.junction):
            raise RuntimeError(
                f"the replay of seed {trace.seed} diverged at stop {trace.steps.index(step)}: "
                f"recorded tick {step.tick} junction {step.junction}, "
                f"replayed tick {view.tick} junction {view.junction}")
        driver.choose(step.action)
    return Takeover(driver, index)


def promote(trace: Trace, index: int, suffix: Sequence[TraceStep],
            outcome: RunOutcome | None) -> Trace:
    """The trace up to `index`, then the new choices. Decision (f): replace."""
    return Trace(seed=trace.seed,
                 enabled_predicates=list(trace.enabled_predicates),
                 enabled_actions=list(trace.enabled_actions),
                 params={pid: dict(vals) for pid, vals in trace.params.items()},
                 steps=list(trace.steps[:index]) + list(suffix),
                 outcome=outcome)


def reinduce(client: InductClient, traces: Sequence[Trace], directory: Path,
             out: Path) -> tuple[Induction, list[Path]]:
    """Write the demonstration set as it now stands and induce over it again."""
    paths = [TraceWriter.write(trace, directory / f"trace-{i}-seed-{trace.seed}.json")
             for i, trace in enumerate(traces)]
    return client.induce(paths, out), paths
