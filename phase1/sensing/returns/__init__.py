"""Sensor returns.

A return is one raw observation: noisy, sometimes ambiguous, sometimes false.
Returns are fused into Belief; they are not truth.
"""
from __future__ import annotations

from .bearing import BearingReturn
from .beacon_fix import BeaconFixReturn
from .cargo import CargoReturn
from .odometry import OdometryReturn
from .range_bearing import RangeBearingReturn

Return = (
    OdometryReturn
    | RangeBearingReturn
    | BearingReturn
    | BeaconFixReturn
    | CargoReturn
)

__all__ = [
    "BearingReturn",
    "BeaconFixReturn",
    "CargoReturn",
    "OdometryReturn",
    "RangeBearingReturn",
    "Return",
]
