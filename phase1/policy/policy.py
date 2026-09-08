"""A decision tree over the cave's blocks, evaluated at decision points -- or a player.

Reads Belief only; never imports truth. The tree is the player's -- one of the two
reference trees today, an induced one after a demonstration -- and the engine it hands
off to is the game's (`motor/`). Between decision points the current action's motor
program drives, unchanged from the hand-written policy this replaces.

A decision point is when the action ended, or when something the tree can see became
true (CAVE-BLOCKS.md 3):

    DP0  the match begins
    DP1  the running program ended, or found it had nothing left to do
    DP2  an enabled predicate rose false -> true, re-armed PREDICATE_REARM_S after its
         last firing edge, so a flicker across a threshold is one stop

**Who answers.** With a tree, the policy answers its own stops by walking it. Without
one -- a demonstration -- the stop is a question, and the policy `waiting`s until
`answer(action)` is called; the sim does not tick while it waits, so the match clock
is stopped for the whole of the asking. Either way the stop is found by `poll(t)` at
the top of the tick, before the world has moved, so a demonstration in which a tree
does the choosing is the same match, tick for tick, as that tree running by itself.
That is the check `--teach-scripted` is measured against.

At a stop the chosen action is applied by one rule set (CAVE-BLOCKS.md 2.2): if it is
the action already running, nothing restarts. If it is another, the running program is
suspended and resumed only if it is picked again straight after (fetch, freeze, fetch
keeps its route and its retry count); otherwise it is dropped. An action with nothing
to do -- fetch with no deposit left, freeze in silence -- is not run: the policy stalls
NOOP_WAIT_S and asks again, visibly, and the stop is not a demonstration of anything.

Recall survives unchanged and overrides the tree for the rest of the match
(CAVE-BLOCKS.md guess 5).
"""
from __future__ import annotations

from ..belief.belief import Belief
from ..motor_command import MotorCommand
from .. import tuning as T
from .block_registry import BlockRegistry
from .decision import Decision
from .decision_node import DecisionNode
from .decision_tree import DecisionTree
from .loadout import Loadout
from .motor.body import Body
from .motor.program import Program
from .motor.run_for_shaft import RunForShaft
from .run_spec import RunSpec
from .stop_view import StopView
from .waypoint import Waypoint

Path = tuple[tuple[str, bool], ...]


class Policy:
    def __init__(self, belief: Belief, loadout: Loadout, shaft_beacon_id: str,
                 registry: BlockRegistry, spec: RunSpec, tree: DecisionTree | None) -> None:
        self.b: Belief = belief
        self.registry: BlockRegistry = registry
        self.loadout: Loadout = loadout
        self.shaft_beacon_id: str = shaft_beacon_id
        self.body: Body = Body(belief, loadout, shaft_beacon_id)
        self.spec: RunSpec = spec
        self.tree: DecisionTree | None = tree
        spec.check(registry)
        # Block-list order, so a trace's columns agree with every other trace's.
        self.enabled: list[str] = list(spec.enabled_predicates)
        self.actions: list[str] = list(spec.enabled_actions)
        self.params: dict[str, dict[str, float]] = spec.params
        if tree is not None:
            outside = sorted(tree.predicates_used() - set(self.enabled)) + sorted(
                tree.actions_used() - set(self.actions))
            if outside:
                raise ValueError(f"tree uses blocks that do not exist in this run: {outside}")
            for pid in tree.predicates_used():
                param = registry.predicate(pid).param
                if param is not None and param not in tree.params.get(pid, {}):
                    raise ValueError(f"tree needs a value of {param} for {pid}")
        self.program: Program | None = None
        self.action: str | None = None
        self.suspended: tuple[str, Program] | None = None
        self.decisions: list[Decision] = []
        self.recalled: bool = False
        self._started: bool = False
        self._prev: dict[str, bool] = {}
        self._last_rise: dict[str, float] = {}
        self._noop_until: float = -1.0
        # The stop found at the last polled tick, and its answer.
        self._polled_t: float | None = None
        self.stop: StopView | None = None
        self._answer: tuple[str, Path] | None = None
        self._deferred: str | None = None      # a mid-tick ending nobody could be asked about

    # ---- the one live command ----------------------------------------------------------
    def recall(self, t: float) -> None:
        """Abort to the nearest shaft. Takes the tree -- or the player -- out of the loop."""
        if self.recalled:
            return
        self.recalled = True
        self.b.log.append((t, "RECALL received"))
        self.program = RunForShaft(self.body, t)
        self.action = None
        self.suspended = None
        self.stop = None
        self._answer = None

    # ---- the stop -----------------------------------------------------------------------------
    @property
    def waiting(self) -> bool:
        """A stop is due and nobody has answered it. The sim must not tick."""
        return self.stop is not None and self._answer is None and not self.recalled

    def poll(self, t: float) -> StopView | None:
        """Is a decision due at tick `t`? Asked once per tick, before the world moves;
        asking again at the same `t` returns the same answer and changes nothing."""
        if self._polled_t == t:
            return self.stop
        if self.waiting:
            # Still unanswered from an earlier tick -- the sim ticked while a question
            # was open, which it is written not to do. Keep the question rather than
            # lose the edge that raised it; the view is read again at this tick.
            assert self.stop is not None
            self._deferred = self.stop.reason
        self._polled_t = t
        self.stop = None
        self._answer = None
        self.body.jam.note_motion(t)
        edges = self._rising_edges(t)
        if self.recalled:
            return None
        reason: str | None = None
        if self._deferred is not None:
            reason, self._deferred = self._deferred, None
        elif not self._started:
            reason = "start"
        elif self.program is not None and self.program.ended:
            reason = f"ended:{self.action}"
            self._retire()
        elif edges:
            reason = f"rose:{edges[0]}"
        elif self.program is not None and self.program.ending(t) is not None:
            # It would end before acting this tick: let it, and ask now, while the
            # match clock is still stopped, rather than after an idle tick.
            ended = self.action
            acted = self.program.step(t)
            assert acted is None and self.program.ended
            reason = f"ended:{ended}"
            self._retire()
        elif self.program is None and t >= self._noop_until:
            reason = "waited"
        if reason is None:
            return None
        self.stop = self._stop_view(t, reason, offer=self.tree is None)
        if self.tree is not None:
            action, path = self.tree.walk(self.b, self.tree.params)
            self._answer = (action, tuple(path))
        return self.stop

    def answer(self, action: str) -> None:
        """The chooser's decision at the stop `poll` found. A player's, usually."""
        if self.stop is None:
            raise RuntimeError("no stop is waiting for an answer")
        if action not in self.actions:
            raise ValueError(f"action does not exist in this run: {action}")
        self._answer = (action, ())

    # ---- per tick -------------------------------------------------------------------------
    def step(self, t: float) -> MotorCommand:
        idle = MotorCommand(heading=self.b.theta)
        stop = self.poll(t)
        if self.recalled:
            assert self.program is not None
            cmd = self.program.step(t)
            return cmd if cmd is not None else idle
        if stop is not None:
            if self._answer is None:
                # Asked and not yet answered: the sim should not have ticked. It stands
                # still; the question is still open at the top of the next tick.
                return idle
            action, path = self._answer
            self._apply(stop, action, path)
            self.stop, self._answer = None, None
        if self.program is None:
            return idle

        cmd = self.program.step(t)
        if cmd is None:
            # Ended before acting and `ending` did not see it coming: with a tree the
            # tick belongs to whatever it picks next, as ever; a demonstration is asked
            # at the top of the next tick and this one is idle.
            ended = self.action
            self._retire()
            if self.tree is None:
                self._deferred = f"ended:{ended}"
                self.b.log.append((t, f"{self._why(self._deferred)} mid-tick; asking next tick"))
                return idle
            view = self._stop_view(t, f"ended:{ended}", offer=False)
            action, path = self.tree.walk(self.b, self.tree.params)
            self._apply(view, action, tuple(path))
            if self.program is not None:
                cmd = self.program.step(t)
        return cmd if cmd is not None else idle

    def _rising_edges(self, t: float) -> list[str]:
        """Enabled predicates that went false -> true this tick and are armed."""
        edges: list[str] = []
        for pid in self.enabled:
            value, _ = self.registry.evaluate(pid, self.b, self.params.get(pid, {}))
            was = self._prev.get(pid, value if not self._started else False)
            self._prev[pid] = value
            if value and not was and self._started:
                if t - self._last_rise.get(pid, -1e9) >= T.PREDICATE_REARM_S:
                    self._last_rise[pid] = t
                    edges.append(pid)
        return edges

    def _retire(self) -> None:
        self.program = None
        self.action = None

    def _stop_view(self, t: float, reason: str, offer: bool) -> StopView:
        """What the chooser sees: every enabled predicate on Belief now. `offer` also
        works out which actions would do anything here, for the block panel; a tree
        is not shown a panel and does not pay for that."""
        b = self.b
        predicates: dict[str, bool] = {}
        raw: dict[str, float] = {}
        for pid in self.enabled:
            value, number = self.registry.evaluate(pid, b, self.params.get(pid, {}))
            predicates[pid] = value
            if self.registry.predicate(pid).param is not None:
                assert number is not None
                raw[pid] = number
        available: dict[str, bool] = {}
        if offer:
            for action in self.actions:
                if action == self.action or (self.suspended is not None
                                             and self.suspended[0] == action):
                    available[action] = True        # it carries on, or resumes
                else:
                    available[action] = not self.registry.motor(action)(self.body, t).noop
        return StopView(t=t, tick=round(t / T.DT), reason=reason,
                        junction=b.survey.nearest_index(b.x, b.y),
                        predicates=predicates, raw=raw, belief=b, available=available)

    def _apply(self, stop: StopView, action: str, path: Path) -> None:
        """The chosen action, by the three rules; the Decision written down."""
        t = stop.t
        self._started = True
        ran = True
        if action == self.action and self.program is not None:
            pass                                  # the same action continues; nothing restarts
        else:
            # The program being displaced, if any, becomes the one suspended program;
            # whatever was suspended before it is dropped unless it is what was just
            # picked, in which case it resumes where it was.
            if self.suspended is not None and self.suspended[0] == action:
                program = self.suspended[1]
                program.resume(t)
            else:
                program = self.registry.motor(action)(self.body, t)
            self.suspended = None
            if self.program is not None and self.action is not None:
                self.suspended = (self.action, self.program)
            if program.noop:
                self.program = None
                self.action = None
                self._noop_until = t + T.NOOP_WAIT_S
                ran = False
            else:
                self.program = program
                self.action = action
        self.decisions.append(Decision(
            t=t, tick=stop.tick, reason=stop.reason, junction=stop.junction,
            predicates=dict(stop.predicates), raw=dict(stop.raw), path=path,
            action=action, ran=ran))
        self.b.log.append((t, f"{self._why(stop.reason)} -> {self.registry.action(action).label}"
                              + ("" if ran else " (nothing to do; waiting)")))

    def _why(self, reason: str) -> str:
        kind, _, what = reason.partition(":")
        if kind == "rose":
            return self.registry.predicate(what).label
        if kind == "ended":
            return f"{self.registry.action(what).label} ended"
        return reason

    # ---- what the display reads ------------------------------------------------------------
    @property
    def doing(self) -> str:
        """One phrase for the headless timeline."""
        if self.recalled:
            return "recalled"
        if self.waiting:
            return "asking"
        if self.action is None:
            return "waiting"
        return self.registry.action(self.action).label

    def target(self) -> Waypoint | None:
        """The waypoint the motor is making for, if any, for the intent line."""
        return None if self.program is None else self.program.target()

    def decision_report(self, t: float) -> list[DecisionNode]:
        """The tree as a graph with live values: every predicate it reads, the path
        the last evaluation took, the chosen action and what its program is doing.

        Read from Belief only. This is the Phase 1 stand-in for the execution trace
        Phase 4 captures from the behaviour-tree VM -- which nodes fired, on what
        predicate values -- and it is what lets the display show the machine deciding
        rather than only the result of a decision. The bars are the point: a value
        creeping toward its threshold shows what the machine is about to decide,
        seconds before it decides it. Without a tree the predicates listed are the
        run's enabled ones and no path is lit.
        """
        b = self.b
        last = self.decisions[-1] if self.decisions else None
        on_path = dict(last.path) if last is not None else {}
        nodes: list[DecisionNode] = [
            DecisionNode("root", self._root_text(), kind="action", active=True, fired=True)]
        order = self.tree.predicates_in_order() if self.tree is not None else self.enabled
        params_of = self.tree.params if self.tree is not None else self.params
        for pid in order:
            pred = self.registry.predicate(pid)
            params = params_of.get(pid, {})
            value, number = self.registry.evaluate(pid, b, params)
            detail, fill = "", -1.0
            if pred.param is not None and number is not None:
                threshold = float(params[pred.param])
                detail = f"{number:.3g} of {threshold:.3g}"
                fill = min(number / threshold, 1.0) if threshold > 0.0 else 1.0
            nodes.append(DecisionNode(
                f"test.{pid}", f"{pred.label}?", "test",
                answer="yes" if value else "no", detail=detail, fill=fill,
                active=pid in on_path and not self.recalled,
                fired=bool(on_path.get(pid, False)) and not self.recalled))
        if self.program is not None:
            nodes.extend(self.program.nodes(t))
        else:
            nodes.append(DecisionNode("act.wait", "NOTHING TO DO", "action",
                                      detail="asking again shortly", active=True, fired=True))
        return nodes

    def _root_text(self) -> str:
        if self.recalled:
            return "RECALLED"
        if self.action is None:
            return "WAITING"
        return self.registry.action(self.action).label.upper()
