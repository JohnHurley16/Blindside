"""A demonstration reopened at one of its stops, for something to finish differently.

`--teach --resume` is this with a person at the window; `--correct` is this with a
tree. Both replay the recorded choices to the stop (`correction.scrub`), take the
new choices through the same `Takeover`, and put the new suffix in place of the old
one (`correction.promote`, PHASE-2-OPEN-QUESTIONS (f)) before inducing over the
whole set again. One class, so the two forms cannot drift apart.

The old trace is moved out of `traces/` before the rewrite is written, because
`--induce` reads every file there: a copy left beside the rewrite would be one more
demonstration carrying the exact contradiction the replacement exists to remove.
"""
from __future__ import annotations

from pathlib import Path

from .. import tuning as T
from ..demo.recording import Recording
from ..demo.run_source import RunSource
from ..demo.trace import Trace
from ..demo.trace_step import TraceStep
from ..demo.trace_writer import TraceWriter
from ..induct_client import InductClient
from ..match.match_view import MatchView
from ..policy.stop_view import StopView
from . import correction
from .correction_result import CorrectionResult
from .takeover import Takeover


class Resume:
    """Demonstration `which` of `recordings`, replayed to stop `index` and waiting there.

    Opening one re-simulates the run, which is the scrub: the same seed opens the
    same cave and the recorded choices are answered at the recorded stops, each
    checked against the tick and place the trace wrote down (`correction.scrub`
    raises if the replay is not the same match). What is left is a `Takeover`
    positioned at the stop, with the match behind it paused and asking.
    """

    def __init__(self, source: RunSource, client: InductClient, workdir: Path,
                 recordings: list[Recording], which: int, index: int) -> None:
        if not 0 <= which < len(recordings):
            raise IndexError(f"demonstration {which} of {len(recordings)}")
        self.client: InductClient = client
        self.workdir: Path = workdir
        self.recordings: list[Recording] = recordings
        self.which: int = which
        self.recording: Recording = recordings[which]
        self.index: int = index
        self.takeover: Takeover = correction.scrub(source, self.recording, index)

    # ---- what the window reads ------------------------------------------------------------
    @property
    def match(self) -> MatchView:
        return self.takeover.match

    @property
    def old(self) -> Trace:
        """The demonstration as it was recorded."""
        return self.recording.trace

    @property
    def count(self) -> int:
        """How many demonstrations the set has."""
        return len(self.recordings)

    @property
    def step(self) -> TraceStep:
        """The old run's step at the stop this resume began at."""
        return self.old.steps[self.index]

    def old_choice(self, recorded: int, stop: StopView) -> str | None:
        """What the old run chose at this stop, if it stopped here at all.

        `recorded` is how many decisions have run so far, so the old run's step with
        that number is the one to compare against; it is the same stop only if the
        tick and the place agree, which they do exactly until the new choices part
        the two runs, and never again after. None is new ground.
        """
        if not 0 <= recorded < len(self.old.steps):
            return None
        old = self.old.steps[recorded]
        if (old.tick, old.junction) != (stop.tick, stop.junction):
            return None
        return old.action

    # ---- the promotion ----------------------------------------------------------------------
    def finish(self) -> CorrectionResult:
        """The run has ended: the new suffix replaces the old one from the stop, the
        old trace is put aside, the set is written and induced over again."""
        match = self.match
        if not match.over:
            raise RuntimeError("the run has not ended; there is nothing to promote yet")
        suffix = self.takeover.suffix()
        old = self.old
        promoted = correction.promote(old, self.index, suffix,
                                      TraceWriter.from_match(match).outcome)
        backup = self._put_aside(old)
        self.recordings[self.which] = Recording(trace=promoted, path=self.recording.path)
        out = self.workdir / "tree.json"
        induction, written = correction.reinduce(self.client, self.recordings, out)
        self.recordings[:] = written
        self.recording = written[self.which]
        rendered = (self.client.render(out)
                    if induction.consistent and induction.path is not None else None)
        old_choices = [s.action for s in old.steps[self.index:]]
        return CorrectionResult(path=self.recording.path, backup=backup, index=self.index,
                                kept=self.index, replaced=len(old.steps) - self.index,
                                new=len(suffix),
                                changed=old_choices != [s.action for s in suffix],
                                induction=induction, rendered=rendered)

    def _put_aside(self, old: Trace) -> Path:
        """The old trace, under its own name, in a folder --induce never reads; a
        second correction of the same run numbers its backup rather than overwriting
        the first."""
        folder = self.workdir / T.CORRECTION_BACKUP_DIR
        path = folder / self.recording.path.name
        n = 0
        while path.exists():
            n += 1
            path = folder / f"{self.recording.path.stem}-{n}.json"
        return TraceWriter.write(old, path)
