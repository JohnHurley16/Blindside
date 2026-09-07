"""Where the agent actually is. Never visible to a policy."""
from __future__ import annotations

import numpy as np


class AgentTruth:
    """The real place, heading and cargo of the agent.

    `last_true_delta` is the motion actually achieved this tick (cells forward,
    radians turned). The sensor layer corrupts it into odometry; the difference is
    drift, and this is the only place drift is born.
    """

    def __init__(self, seed: int, node: int, heading: float) -> None:
        self.node: int | None = node          # the node it is stopped at, or None
        self.passage: int | None = None       # the passage it is walking, or None
        self.along: float = 0.0               # cells from the passage's near end
        self.direction: int = 1               # +1 toward far, -1 toward near
        self.heading: float = heading
        self.cargo: int = 0
        rng = np.random.default_rng([seed, 1])
        # The bias leans one way for the whole run, drawn from the seed.
        self.drift_sign_scale: float = 1.0 if rng.random() < 0.5 else -1.0
        self.drift_sign_heading: float = 1.0 if rng.random() < 0.5 else -1.0
        self.last_true_delta: tuple[float, float] = (0.0, 0.0)

    @property
    def stopped(self) -> bool:
        return self.node is not None

    def __repr__(self) -> str:
        return (f"<AgentTruth node={self.node} passage={self.passage} along={self.along:.1f} "
                f"cargo={self.cargo}>")
