"""The staged tutorial, the induction, and the correction loop, as a state machine.

Nothing in here draws: the window reads this and the scripted run pumps it. It also
builds no World -- runs are opened through the `RunSource` it is handed, which is
what keeps the whole of `view` on the belief side of the sensor layer.

The order is the spec's: three staged runs (the first with no drift and only the
blocks marked stage 1, the next two with drift and the whole list), three
demonstrations on fresh seeds, then induce. After that comes the loop the gate is
timed on: ghost a demonstration against the induced tree, scrub to the stop where
they first differed, take over, promote that suffix in place of the old one, induce
again. The clock runs from the scrub to the second induction's answer.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from ..demo.recording import Recording
from ..demo.run_driver import RunDriver
from ..demo.run_source import RunSource
from ..demo.stage import Stage
from ..demo.stop_view import StopView
from ..demo.trace import Trace
from ..demo.trace_step import TraceStep
from ..demo.trace_writer import TraceWriter
from ..demo.tutorial import Tutorial
from ..induct_client import InductClient
from ..policy.block_registry import BlockRegistry
from ..policy.decision_tree import DecisionTree
from ..replay import correction
from ..replay.ghost import Ghost
from ..replay.ghost_result import GhostResult
from ..replay.takeover import Takeover
from ..seam.induction import Induction
from ..seam.rendered import Rendered
from .phase import Phase
from .tree_path import lit_lines

Chooser = Callable[[StopView], str]
ChooserFor = Callable[[Stage], Chooser]


class SessionController:
    """One session: six runs, one induction, one correction."""

    def __init__(self, source: RunSource, registry: BlockRegistry, tutorial: Tutorial,
                 client: InductClient, workdir: Path,
                 chooser_for: ChooserFor | None = None) -> None:
        self.source: RunSource = source
        self.registry: BlockRegistry = registry
        self.tutorial: Tutorial = tutorial
        self.client: InductClient = client
        self.workdir: Path = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.chooser_for: ChooserFor | None = chooser_for
        self.auto: bool = chooser_for is not None

        self.stage_index: int = 0
        self.phase: Phase = Phase.STOP
        self.driver: RunDriver | None = None
        self.stop: StopView | None = None
        self.last_stop: StopView | None = None
        self.trace: Trace | None = None
        self.recordings: list[Recording] = []
        self.message: str = ""
        self.log: list[str] = []

        self.tree_path: Path | None = None
        self.induction: Induction | None = None
        self.rendered: Rendered | None = None
        self.ghost: GhostResult | None = None
        self.ghost_recording: Recording | None = None
        self.ghosts_tried: int = 0
        self.scrub_index: int = 0
        self.takeover: Takeover | None = None
        self.correction_seconds: float | None = None
        self.reinduction: Induction | None = None
        self.seam_check: str = ""
        self._clock_start: float | None = None
        self._begin_stage()

    # ---- what the window reads -----------------------------------------------------------
    @property
    def stage(self) -> Stage:
        return self.tutorial.stages[min(self.stage_index, len(self.tutorial.stages) - 1)]

    @property
    def enabled_predicates(self) -> list[str]:
        return self.tutorial.predicates(self.stage)

    @property
    def enabled_actions(self) -> list[str]:
        return self.tutorial.actions(self.stage)

    @property
    def params(self) -> dict[str, dict[str, float]]:
        return self.stage.params

    @property
    def offered_actions(self) -> list[str]:
        """The actions the keys 1..n are bound to right now. A takeover is a run of
        the stage its demonstration came from, not of the stage the tutorial is on."""
        if self.phase is Phase.TAKEOVER and self.ghost_recording is not None:
            return list(self.ghost_recording.trace.enabled_actions)
        return self.enabled_actions

    @property
    def offered_predicates(self) -> list[str]:
        if self.phase is Phase.TAKEOVER and self.ghost_recording is not None:
            return list(self.ghost_recording.trace.enabled_predicates)
        return self.enabled_predicates

    @property
    def offered_params(self) -> dict[str, dict[str, float]]:
        if self.phase is Phase.TAKEOVER and self.ghost_recording is not None:
            return {p: dict(v) for p, v in self.ghost_recording.trace.params.items()}
        return self.params

    def say(self, text: str) -> None:
        self.message = text
        self.log.append(text)

    def hints(self) -> str:
        keys = "    ".join(f"[{i + 1}] {self.registry.action(a).label}"
                           for i, a in enumerate(self.offered_actions))
        if self.phase is Phase.STOP:
            return keys
        if self.phase is Phase.RUN_OVER:
            return ("[SPACE] next run" if self.stage_index + 1 < len(self.tutorial.stages)
                    else "[SPACE] induce a rule from what you did")
        if self.phase is Phase.INDUCED:
            return "[G] run the rule beside a demonstration"
        if self.phase in (Phase.GHOST, Phase.SCRUB):
            return "[LEFT] [RIGHT] scrub    [T] take over from this stop"
        if self.phase is Phase.TAKEOVER:
            if self.takeover is not None and self.takeover.done:
                return "[P] promote what you just did"
            return f"{keys}    (the run has to end before you can promote it)"
        if self.phase is Phase.PROMOTED:
            return "the loop is closed"
        return ""

    # ---- the runs ---------------------------------------------------------------------------
    def _begin_stage(self) -> None:
        stage = self.stage
        self.driver = self.source.open(stage.seed,
                                       enabled_predicates=self.enabled_predicates,
                                       enabled_actions=self.enabled_actions,
                                       params=self.params, drift=stage.drift)
        self.trace = Trace(seed=self.driver.seed,
                           enabled_predicates=list(self.driver.enabled_predicates),
                           enabled_actions=list(self.driver.enabled_actions),
                           params={p: dict(v) for p, v in self.driver.params.items()})
        self.phase = Phase.STOP
        self.say(f"run {stage.number} of {len(self.tutorial.stages)}: {stage.title.lower()}")
        self._advance()

    def _advance(self) -> None:
        assert self.driver is not None and self.trace is not None
        self.stop = self.driver.advance_to_stop()
        if self.stop is not None:
            self.last_stop = self.stop
            return
        self.trace.outcome = self.driver.outcome
        path = TraceWriter.write(
            self.trace,
            self.workdir / f"trace-{len(self.recordings)}-seed-{self.trace.seed}.json")
        self.recordings.append(Recording(stage=self.stage, trace=self.trace, path=path))
        outcome = self.trace.outcome
        assert outcome is not None
        self.phase = Phase.RUN_OVER
        self.say(f"run {self.stage.number} ended: {outcome.reason}, "
                 f"{len(self.trace.steps)} stops, {outcome.ticks} ticks")

    def choose(self, action: str) -> None:
        """Make the decision at the stop the run is waiting on."""
        if self.phase is Phase.TAKEOVER:
            self._takeover_choose(action)
            return
        if self.phase is not Phase.STOP or self.stop is None or self.trace is None:
            return
        view = self.stop
        step = TraceStep(tick=view.tick, junction=view.junction,
                         predicates=dict(view.predicates),
                         raw=dict(view.raw), action=action)
        assert self.driver is not None
        # Written down only if it happened; see `match/session.py:choose`.
        if self.driver.choose(action):
            self.trace.steps.append(step)
        self._advance()

    def next_stage(self) -> None:
        if self.phase is not Phase.RUN_OVER:
            return
        if self.stage_index + 1 < len(self.tutorial.stages):
            self.stage_index += 1
            self._begin_stage()
        else:
            self.induce()

    # ---- the induction ------------------------------------------------------------------------
    def induce(self) -> None:
        out = self.workdir / "induced.json"
        self.induction = self.client.induce([r.path for r in self.recordings], out)
        if self.induction.consistent and self.induction.path is not None:
            self.tree_path = self.induction.path
            self.rendered = self.client.render(self.tree_path)
            self.say(f"the rule: {self.rendered.sentence}")
        else:
            self.tree_path = None
            self.rendered = None
            query = self.induction.query
            first = query.text.splitlines()[0] if query is not None else ""
            self.say(f"no rule fits everything you did. {first}")
        self.phase = Phase.INDUCED

    # ---- the ghost -----------------------------------------------------------------------------
    def run_ghost(self) -> None:
        """Replay the induced tree beside the demonstrations and stop at the first one
        it disagrees with."""
        if self.phase is not Phase.INDUCED or self.tree_path is None:
            return
        ghost = Ghost(self.source, self.registry, self.client)
        tree = DecisionTree.load(self.tree_path, self.registry)
        runnable = [r for r in self.recordings if ghost.can_run(r, tree)]
        if not runnable:
            self.say("the rule names blocks no recorded run had; there is nothing to ghost")
            return
        chosen: Recording = runnable[-1]
        result: GhostResult | None = None
        self.ghosts_tried = 0
        for recording in runnable:
            result = ghost.run(recording, self.tree_path)
            chosen = recording
            self.ghosts_tried += 1
            if result.first_difference is not None:
                break
        assert result is not None
        self.ghost = result
        self.ghost_recording = chosen
        # The scrub starts where the tree and the demonstration first parted. When they
        # never parted there is nothing the ghost is pointing at, so it starts at the
        # last stop, which is where a player who wanted to change something would begin.
        self.scrub_index = (result.first_difference if result.first_difference is not None
                            else max(len(chosen.trace.steps) - 1, 0))
        self.phase = Phase.GHOST
        self.seam_check = self._check_seam(chosen, result)
        tried = ("" if result.first_difference is not None or self.ghosts_tried < 2
                 else f", and on the {self.ghosts_tried - 1} runs before it")
        self.say(f"ghost on seed {result.seed}: {result.summary()}{tried}")

    def _check_seam(self, recording: Recording, result: GhostResult) -> str:
        """Ask the induction what its own tree does at every stop the ghost made.

        Three readings of the same tree have to agree or the window is lying: the
        Python interpreter that drove the ghost from Belief, the local walk that
        lights the panel's lines, and `induct decide`, which is the seam's own
        authority. This is the only caller of `decide`, and it is here because a
        disagreement would show up as a lit path that does not match the choice
        under it.
        """
        induction = self.reinduction or self.induction
        if self.tree_path is None or induction is None or induction.tree is None:
            return ""
        root = induction.tree["root"]
        params = induction.tree.get("params", {})
        disagreements = 0
        for step in result.steps:
            _, local = lit_lines(root, self.registry, params, step.predicates, step.raw)
            remote = self.client.decide(self.tree_path, step.predicates, step.raw)
            if not (local == remote == step.action):
                disagreements += 1
        if disagreements:
            return (f"SEAM DISAGREEMENT at {disagreements} of {len(result.steps)} stops: "
                    f"the panel, the sim and induct decide do not read this tree alike")
        return (f"seam check: the sim, the panel and induct decide agree at all "
                f"{len(result.steps)} stops of seed {recording.trace.seed}")

    def scrub(self, delta: int) -> None:
        if self.ghost_recording is None or self.phase not in (Phase.GHOST, Phase.SCRUB):
            return
        if self._clock_start is None:
            self._clock_start = time.perf_counter()
        last = len(self.ghost_recording.trace.steps) - 1
        self.scrub_index = max(0, min(last, self.scrub_index + delta))
        self.phase = Phase.SCRUB
        self.say(f"stop {self.scrub_index} of {last + 1}, seed "
                 f"{self.ghost_recording.trace.seed}")

    def take_over(self) -> None:
        """Re-simulate to the scrub point and hand the run back."""
        if self.ghost_recording is None or self.phase not in (Phase.GHOST, Phase.SCRUB):
            return
        if self._clock_start is None:
            self._clock_start = time.perf_counter()
        self.takeover = correction.scrub(self.source, self.ghost_recording, self.scrub_index)
        self.stop = self.takeover.stop
        if self.stop is not None:
            self.last_stop = self.stop
        self.phase = Phase.TAKEOVER
        self.say(f"you have the run from stop {self.scrub_index}; choose, then promote")

    def _takeover_choose(self, action: str) -> None:
        assert self.takeover is not None
        if self.takeover.done:
            return
        self.takeover.choose(action)
        self.stop = self.takeover.stop
        if self.stop is not None:
            self.last_stop = self.stop

    def promote(self) -> None:
        """Replace the demonstration's suffix with what was just done, then induce again."""
        if self.phase is not Phase.TAKEOVER or self.takeover is None \
                or self.ghost_recording is None:
            return
        chooser = None if self.chooser_for is None \
            else self.chooser_for(self.ghost_recording.stage)
        while not self.takeover.done and chooser is not None:
            stop = self.takeover.stop
            assert stop is not None
            self.takeover.choose(chooser(stop))
        if not self.takeover.done:
            # A trace without an outcome is not a demonstration, and the contract's
            # trace.json has nowhere to put "still going". Finish the run first.
            self.say("the run has to end before you can promote it; keep choosing")
            return
        original = self.ghost_recording
        promoted = correction.promote(original.trace, self.scrub_index,
                                      self.takeover.steps, self.takeover.outcome)
        changed = ([s.action for s in original.trace.steps[self.scrub_index:]]
                   != [s.action for s in self.takeover.steps])
        index = self.recordings.index(original)
        self.recordings[index] = Recording(stage=original.stage, trace=promoted,
                                           path=original.path)
        out = self.workdir / "induced-2.json"
        self.reinduction, paths = correction.reinduce(
            self.client, [r.trace for r in self.recordings], self.workdir, out)
        self.recordings = [Recording(stage=r.stage, trace=r.trace, path=p)
                           for r, p in zip(self.recordings, paths)]
        self.ghost_recording = self.recordings[index]
        if self.reinduction.consistent and self.reinduction.path is not None:
            self.tree_path = self.reinduction.path
            self.rendered = self.client.render(self.tree_path)
        if self._clock_start is not None:
            self.correction_seconds = time.perf_counter() - self._clock_start
        self.phase = Phase.PROMOTED
        self.say(f"promoted stop {self.scrub_index} onward "
                 f"({'the suffix changed' if changed else 'the suffix came back identical'}); "
                 f"re-induced: "
                 f"{'consistent' if self.reinduction.consistent else 'INCONSISTENT'}")

    # ---- input ---------------------------------------------------------------------------------
    def key(self, name: str) -> None:
        name = name.lower()
        if name.isdigit():
            index = int(name) - 1
            actions = self.offered_actions
            if 0 <= index < len(actions):
                self.choose(actions[index])
        elif name == "space":
            self.next_stage()
        elif name == "g":
            self.run_ghost()
        elif name == "left":
            self.scrub(-1)
        elif name == "right":
            self.scrub(1)
        elif name == "t":
            self.take_over()
        elif name == "p":
            self.promote()

    # ---- the scripted session -------------------------------------------------------------------
    def pump(self) -> bool:
        """One unit of work with the scripted chooser. False when the session is done."""
        if not self.auto or self.chooser_for is None:
            return self.phase is not Phase.DONE
        if self.phase is Phase.STOP and self.stop is not None:
            self.choose(self.chooser_for(self.stage)(self.stop))
            return True
        if self.phase is Phase.RUN_OVER:
            self.next_stage()
            return True
        if self.phase is Phase.INDUCED:
            if self.tree_path is None:
                self.phase = Phase.DONE
                return True
            self.run_ghost()
            if self.phase is not Phase.GHOST:
                self.phase = Phase.DONE
            return True
        if self.phase is Phase.GHOST:
            self.scrub(0)
            return True
        if self.phase is Phase.SCRUB:
            self.take_over()
            return True
        if self.phase is Phase.TAKEOVER:
            self.promote()
            return True
        if self.phase is Phase.PROMOTED:
            self.phase = Phase.DONE
            return True
        return False
