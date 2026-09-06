"""Ground truth, drawn over belief, only once the match is over.

DESIGN puts truth in exactly two places, and the post-match replay is one of them.
Without it a player leaves not knowing whether they were fooled, and the playtest
loses most of its signal -- so this is where the wrong theory gets corrected.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class Reveal:
    walls: np.ndarray
    flooded: np.ndarray
    agents: dict[str, tuple[float, float, bool, bool]]
    beacons: dict[str, tuple[float, float, str]]
    ancient: tuple[float, float, float]
    deposits: dict[str, tuple[float, float]]
    truth_trail: dict[str, list[tuple[float, float, float]]]
