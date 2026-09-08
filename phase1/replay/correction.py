"""Scrub to a stop, take over from there, promote what you did, induce again.

`PHASE-2-OPEN-QUESTIONS.md` (f) is the rule this file implements: a correction
means *the rule I taught was wrong from here*, so the promoted demonstration is
the original trace up to the scrub point plus the new choices after it --
**replaced, not appended**. Appending would leave the wrong choice in the evidence
and fire the contradiction query on the player's own mistake.

The re-simulation is exact rather than approximate: the same seed opens the same
cave, the same rival and the same sensor streams, and answering the recorded
choices at the recorded stops reproduces them. `scrub` checks that, stop by stop,
and refuses if it does not. A stop where a no-op was chosen is not in the trace and
cannot be replayed, which is why the teach window refuses a no-op key.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from ..demo.recording import Recording
from ..demo.run_outcome import RunOutcome
from ..demo.run_source import RunSource
from ..demo.trace import Trace
from ..demo.trace_step import TraceStep
from ..demo.trace_writer import TraceWriter
from ..induct_client import InductClient
from ..policy.run_spec import RunSpec
from ..seam.induction import Induction
from .takeover import Takeover


def scrub(source: RunSource, recording: Recording, index: int) -> Takeover:
    """Re-simulate the match to stop `index` and hand it to a chooser.

    Every stop before `index` replays the choice the demonstration recorded there;
    the tick and place it lands on must be the ones the trace wrote down, or the
    replay is not the same match and the correction would be about a different one.
    """
    trace = recording.trace
    if not 0 <= index < len(trace.steps):
        raise IndexError(f"stop {index} is outside the {len(trace.steps)} the run has")
    spec = RunSpec.from_trace(trace.enabled_predicates, trace.enabled_actions, trace.params)
    match = source.open(trace.seed, spec, None)
    for k, step in enumerate(trace.steps[:index]):
        view = match.advance_to_stop()
        if view is None:
            raise RuntimeError(f"the replay of seed {trace.seed} ended before stop {index}")
        if (view.tick, view.junction) != (step.tick, step.junction):
            raise RuntimeError(
                f"the replay of seed {trace.seed} diverged at stop {k}: "
                f"recorded tick {step.tick} place {step.junction}, "
                f"replayed tick {view.tick} place {view.junction}")
        match.answer(step.action)
    view = match.advance_to_stop()
    if view is None:
        raise RuntimeError(f"the replay of seed {trace.seed} ended before stop {index}")
    step = trace.steps[index]
    if (view.tick, view.junction) != (step.tick, step.junction):
        raise RuntimeError(
            f"the replay of seed {trace.seed} diverged at stop {index}: "
            f"recorded tick {step.tick} place {step.junction}, "
            f"replayed tick {view.tick} place {view.junction}")
    return Takeover(match, index, before=index)


def promote(trace: Trace, index: int, suffix: Sequence[TraceStep],
            outcome: RunOutcome | None) -> Trace:
    """The trace up to `index`, then the new choices. Decision (f): replace."""
    return Trace(seed=trace.seed,
                 enabled_predicates=list(trace.enabled_predicates),
                 enabled_actions=list(trace.enabled_actions),
                 params={pid: dict(vals) for pid, vals in trace.params.items()},
                 steps=list(trace.steps[:index]) + list(suffix),
                 outcome=outcome)


def reinduce(client: InductClient, recordings: Sequence[Recording],
             out: Path) -> tuple[Induction, list[Recording]]:
    """Write the demonstration set as it now stands, each to its own file, and induce
    over it again."""
    written = [Recording(trace=r.trace, path=TraceWriter.write(r.trace, r.path))
               for r in recordings]
    return client.induce([r.path for r in written], out), written
