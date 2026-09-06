"""Ground truth.

**Only `phase1.sensing` and `phase1.match` may import this package.** `phase1.belief`
and `phase1.policy` must not, and there is a check for that in
`phase1.match.invariant`. See the invariant in CLAUDE.md: an agent's policy may
never observe ground truth.
"""
from __future__ import annotations

from .agent_truth import AgentTruth
from .ancient import Ancient
from .beacon import Beacon
from .pending_sound import PendingSound
from .world import World
from .world_event import WorldEvent

__all__ = ["AgentTruth", "Ancient", "Beacon", "PendingSound", "World", "WorldEvent"]
