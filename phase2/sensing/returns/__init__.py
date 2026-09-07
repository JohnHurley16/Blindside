"""Sensor returns.

A return is one raw observation: noisy, sometimes wrong. Returns are fused into
Belief; they are not truth.
"""
from __future__ import annotations

from .cargo import CargoReturn
from .junction_return import JunctionReturn
from .odometry import OdometryReturn
from .shaft_fix import ShaftFixReturn

Return = OdometryReturn | JunctionReturn | ShaftFixReturn | CargoReturn

__all__ = ["CargoReturn", "JunctionReturn", "OdometryReturn", "ShaftFixReturn", "Return"]
