"""Everything the renderer is allowed to hold. SPECTATOR-DISPLAY.md section 4.2, rule 8.

Rules 4 and 5 of the invariant are name-based AST walks, and a name-based walk will
miss `getattr(self.sim, "world")`, a re-export, or a module-level alias. This facade
removes the reachability rather than detecting the reach: `View` is handed one of
these instead of a `Sim`, and every member of it returns either nothing, a Belief, a
Policy, or a frozen `StageFrame`. None of those is, or holds, a `World`.

The one route that remains is the private `__sim`, name-mangled to `_MatchView__sim`;
`match/invariant.py` rule 4 forbids the renderer from writing either spelling. That is
the ceiling in Python and section 4.3 says so plainly: reflection walks to any loaded
class without importing anything, and that is deliberate malice rather than the
accident this guards against.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .sim import Sim

if TYPE_CHECKING:                       # pragma: no cover - types only
    from ..belief.belief import Belief
    from ..policy.policy import Policy
    from .match_result import MatchResult
    from .reveal import Reveal
    from .stage_frame import StageFrame


class MatchView:
    """A read-and-drive view of one match, with no route to ground truth."""

    def __init__(self, sim: Sim) -> None:
        self.__sim: Sim = sim

    # ---- where the match is -------------------------------------------------------
    @property
    def t(self) -> float:
        return self.__sim.t

    @property
    def tick(self) -> int:
        return self.__sim.tick

    @property
    def over(self) -> bool:
        return self.__sim.over

    @property
    def result(self) -> MatchResult | None:
        return self.__sim.result

    # ---- the one player input -----------------------------------------------------
    @property
    def recall_used(self) -> bool:
        return self.__sim.recall_used

    @property
    def recall_pending(self) -> bool:
        return self.__sim.recall_pending

    def recall(self) -> bool:
        return self.__sim.recall()

    # ---- what the machines think --------------------------------------------------
    @property
    def beliefs(self) -> dict[str, Belief]:
        return self.__sim.beliefs

    @property
    def policies(self) -> dict[str, Policy]:
        return self.__sim.policies

    # ---- driving ------------------------------------------------------------------
    def advance_to(self, target_t: float, max_steps: int = 1 << 30) -> int:
        """Step the match up to `target_t`. Returns the number of ticks taken.

        The clock lives here rather than in the renderer so that nothing in `view/`
        has to hold a `Sim` at all -- the recorder used to, which quietly defeated the
        point of the facade.
        """
        steps = 0
        while self.__sim.t < target_t and not self.__sim.over and steps < max_steps:
            self.__sim.step()
            if self.__sim.tick % 10 == 0:
                self.__sim.record_truth_trail()
            steps += 1
        return steps

    # ---- truth, one way, to the screen ---------------------------------------------
    def stage(self) -> StageFrame:
        return self.__sim.stage()

    def reveal(self) -> Reveal:
        return self.__sim.reveal()

    # ---- what the facade is, as data, so the invariant can assert on it -------------
    MEMBERS: tuple[str, ...] = (
        "t", "tick", "over", "result", "recall_used", "recall_pending", "recall",
        "beliefs", "policies", "advance_to", "stage", "reveal", "MEMBERS",
    )
