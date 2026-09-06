"""A ranged return: active sonar, near-field, or nothing at all."""
from __future__ import annotations

from dataclasses import dataclass

from ...point_source import PointSource


@dataclass(slots=True, frozen=True)
class RangeBearingReturn:
    """Range and bearing in the agent's body frame.

    Becomes a point in the map once Belief places it using the pose estimate it
    holds *at this instant* -- which is why the map smears as that estimate drifts.
    """
    range: float
    bearing_body: float
    quality: float
    source: PointSource
