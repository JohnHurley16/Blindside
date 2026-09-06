"""Scripted behaviour.

**This package must never import `phase1.truth`.** A policy reads `Belief` and
nothing else -- that is the one invariant the whole project rests on.
"""
from __future__ import annotations

from .policy import Policy
from .policy_mode import PolicyMode
from .waypoint import Waypoint

__all__ = ["Policy", "PolicyMode", "Waypoint"]
