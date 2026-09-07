"""Ground truth, drawn over belief, only once the match is over.

DESIGN puts truth in exactly two places, and the post-match replay is one of them.
Without it a player leaves not knowing whether they were fooled, and the playtest
loses most of its signal -- so this is where the wrong theory gets corrected.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class Reveal:
    """Frozen plain data, like StageFrame and for the same reason.

    This is the second half of the truth channel and it sits on the facade the renderer
    holds, so it gets the same treatment: nothing on it is a live handle. `truth_trail` used
    to be Sim's own dict, which meant the renderer could append to the simulation's history;
    it is copied to tuples at the boundary now. The arrays are made read-only for the same
    reason -- a renderer bug must not be able to write into truth.
    """

    walls: np.ndarray
    flooded: np.ndarray
    agents: dict[str, tuple[float, float, bool, bool]]
    beacons: dict[str, tuple[float, float, str]]
    ancient: tuple[float, float, float]
    deposits: dict[str, tuple[float, float]]
    truth_trail: dict[str, tuple[tuple[float, float, float], ...]]
