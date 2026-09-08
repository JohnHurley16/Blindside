"""The six runs, built from the block list.

The tutorial introduces blocks the way a first night introduces a pickaxe: run one
has no drift and only the blocks marked stage 1; drift arrives with run two and the
rest of the list appears, because now it can matter; run three is the full problem
again on a harder seed. Three demonstrations follow on three fresh seeds, and those
three are the ones the gate's success rate is measured from.

Nothing here names a block. Which blocks a run has is the `stage` field on the
block list; how many staged runs there are is how many distinct stages it carries.
"""
from __future__ import annotations

from typing import Mapping

from .. import tuning as T
from ..policy.block_registry import BlockRegistry
from .stage import Stage


class Tutorial:
    """The stage list, and the enabled block ids for any one of them."""

    def __init__(self, registry: BlockRegistry) -> None:
        self.registry: BlockRegistry = registry
        self.stages: list[Stage] = self._build()

    def _params(self, block_stage: int) -> dict[str, dict[str, float]]:
        """Every parametric predicate that exists by this run needs a value of its
        parameter for its boolean to exist at all. The value is the provisional one
        beside the block on the list: the induction refits it from the raw numbers
        the trace carries."""
        return self.registry.provisional_params(self.registry.predicate_ids_by_stage(block_stage))

    def _build(self) -> list[Stage]:
        full = self.registry.last_stage()
        stages: list[Stage] = [
            Stage(number=1, title="LEARNING THE FIRST BLOCKS", seed=T.TUTORIAL_SEEDS[0],
                  note="dead reckoning is exact here. Nothing can get lost yet.",
                  drift=False, block_stage=1, demonstration=False, params=self._params(1)),
            Stage(number=2, title="DRIFT ARRIVES", seed=T.TUTORIAL_SEEDS[1],
                  note="the estimate is wrong now, and the rest of the blocks exist "
                       "because that is what makes them worth anything.",
                  drift=True, block_stage=full, demonstration=False, params=self._params(full)),
            Stage(number=3, title="THE FULL PROBLEM", seed=T.TUTORIAL_SEEDS[2],
                  note="every block, drift on. Teach it what you want it to do.",
                  drift=True, block_stage=full, demonstration=False, params=self._params(full)),
        ]
        for index, seed in enumerate(T.DEMONSTRATION_SEEDS):
            stages.append(Stage(number=4 + index, title=f"DEMONSTRATION {index + 1} OF 3",
                                seed=seed, note="a seed you have not seen.",
                                drift=True, block_stage=full, demonstration=True,
                                params=self._params(full)))
        return stages

    # ---- what a run is given ------------------------------------------------------------
    def predicates(self, stage: Stage) -> list[str]:
        return self.registry.predicate_ids_by_stage(stage.block_stage)

    def actions(self, stage: Stage) -> list[str]:
        return self.registry.action_ids_by_stage(stage.block_stage)

    def params(self, stage: Stage) -> Mapping[str, Mapping[str, float]]:
        return stage.params
