"""One run of one corridor: the loop that holds World, the rig and Belief.

This is the only place, besides the sensor rig and the evaluator's reveal, where
World and Belief are both in scope. The policy side sees it only through the
`RunDriver` protocol: a stop view in, an action id out. The reveal counters here
(misturns) read both and exist for the post-run table only.
"""
from __future__ import annotations

from typing import Iterable, Mapping

from .. import tuning as T
from ..belief.belief import Belief
from ..demo.stop_view import StopView
from ..eval.run_outcome import RunOutcome
from ..policy.block_registry import BlockRegistry
from ..sensing.sensor_rig import SensorRig
from ..truth.world import World


class Session:
    """Steps the world, senses, updates belief, and stops for decisions."""

    def __init__(self, world: World, registry: BlockRegistry, *,
                 enabled_predicates: Iterable[str] | None = None,
                 enabled_actions: Iterable[str] | None = None,
                 params: Mapping[str, Mapping[str, float]] | None = None,
                 drift: bool = True) -> None:
        self.world: World = world
        self.seed: int = world.seed
        self.registry: BlockRegistry = registry
        self.enabled_predicates: list[str] = list(enabled_predicates
                                                  if enabled_predicates is not None
                                                  else registry.predicate_ids())
        self.enabled_actions: list[str] = list(enabled_actions
                                               if enabled_actions is not None
                                               else registry.action_ids())
        self.params: dict[str, dict[str, float]] = {
            pid: {k: float(v) for k, v in vals.items()} for pid, vals in (params or {}).items()
        }
        for pid in self.enabled_predicates:
            param = registry.predicate(pid).param
            if param is not None and param not in self.params.get(pid, {}):
                raise ValueError(f"{pid} is enabled and needs a value of {param}")
        self.rig: SensorRig = SensorRig(world.seed, drift=drift)
        self.belief: Belief = Belief()
        self.tick: int = 0
        self.budget: int = T.BUDGET_FACTOR * world.corridor.dfs_walk_ticks()
        self.outcome: RunOutcome | None = None
        self.stops: int = 0
        self.misturns: int = 0
        self.first_misturn_stop: int | None = None
        # Reveal only, like the misturn counters: where the body actually went, for
        # the after-the-run overlay. Nothing reads it until the run is over.
        self.truth_trail: list[tuple[float, float]] = [world.position()]
        self._decided: bool = False
        self._hold_until: int | None = None
        self._sample()

    # ---- the loop -------------------------------------------------------------------------
    def advance_to_stop(self) -> StopView | None:
        """Run until the agent is stopped and waiting for a decision, or the run ends."""
        while self.outcome is None:
            me = self.world.agent
            if me.stopped and not self._decided:
                self._decided = True
                self.stops += 1
                return self._stop_view()
            if self._hold_until is not None:
                self.world.hold()
            self.world.step()
            self.tick += 1
            self._sample()
            if self.tick % T.TRUTH_TRAIL_EVERY_TICKS == 0:
                self.truth_trail.append(self.world.position())
            if self.world.in_shaft_range() and me.cargo > 0:
                self._end(True, False, "success")
            elif self._hold_until is not None:
                if self.belief.fixed_here:
                    self._hold_until = None
                    self._decided = False
                elif self.tick >= self._hold_until:
                    self._end(False, True, "lost")
            if self.outcome is None and self.tick >= self.budget:
                self._end(False, False, "budget")
        return None

    def choose(self, action: str) -> bool:
        """Apply a decision at the current stop. True when the body actually left.

        The return value matters to a demonstration and to nothing else: an action
        whose motor holds did not happen, so it is not evidence of anything. The
        case that forces it is the tutorial's first run, where one action exists and
        the agent eventually stands somewhere it cannot be used -- recorded, that
        stop says "no unexplored branch here, so take a branch", which is a rule
        nobody meant and which contradicts every full run. See `demo/demonstration.py`.
        """
        if self.outcome is not None:
            raise RuntimeError("the run is over")
        if action not in self.enabled_actions:
            raise ValueError(f"action does not exist in this run: {action}")
        command = self.registry.motor(action)(self.belief)
        if command.go:
            intent = self.belief.walking
            node = self.world.agent.node
            assert intent is not None and node is not None
            taken = self.world.depart(command.turn)
            self._note_turn(intent[1], node, taken)
            self._decided = False
            return True
        if self.belief.at_shaft():
            if self.belief.fixed_here:
                self._end(False, False, "home-empty")
            else:
                self._hold_until = self.tick + T.LOST_ALLOWANCE_TICKS
        else:
            self._end(False, False, "stuck")
        return False

    # ---- pieces --------------------------------------------------------------------------------
    def _sample(self) -> None:
        self.belief.update(self.rig.sample(self.world), self.tick)

    def _end(self, success: bool, lost: bool, reason: str) -> None:
        self.outcome = RunOutcome(success=success, ticks=self.tick, lost=lost, reason=reason)

    def _stop_view(self) -> StopView:
        predicates: dict[str, bool] = {}
        raw: dict[str, float] = {}
        for pid in self.enabled_predicates:
            value, number = self.registry.evaluate(pid, self.belief, self.params.get(pid, {}))
            predicates[pid] = value
            if self.registry.predicate(pid).param is not None:
                assert number is not None
                raw[pid] = number
        assert self.belief.current is not None
        return StopView(tick=self.tick, junction=self.belief.current,
                        predicates=predicates, raw=raw, belief=self.belief)

    def _note_turn(self, index: int | None, node: int, taken: int) -> None:
        """Reveal only: did the body go where belief meant it to? Belief's intent is
        'back' or 'the i-th onward mouth, left-most first'; truth orders the same way."""
        corridor = self.world.corridor
        if index is None:
            intended = corridor.nodes[node].parent
        else:
            onward = corridor.children(node)
            intended = onward[index] if index < len(onward) else None
        if intended != taken:
            self.misturns += 1
            if self.first_misturn_stop is None:
                self.first_misturn_stop = self.stops
