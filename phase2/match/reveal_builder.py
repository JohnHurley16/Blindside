"""Build the after-the-run reveal from World.

**This module reads ground truth**, which is why it lives in `match` and not in
`reveal`. It flattens a finished run into plain numbers; what it returns has no
route back to World, and the window is handed one only once the run is over.
"""
from __future__ import annotations

from ..reveal.truth_snapshot import TruthSnapshot
from .session import Session


class RevealBuilder:
    """One finished session in, one snapshot out."""

    @staticmethod
    def of(session: Session) -> TruthSnapshot:
        corridor = session.world.corridor
        nodes = [(n.x, n.y) for n in corridor.nodes.values()]
        passages = [(corridor.nodes[p.near].x, corridor.nodes[p.near].y,
                     corridor.nodes[p.far].x, corridor.nodes[p.far].y)
                    for p in corridor.passages.values()]
        deposit = corridor.nodes[corridor.deposit]
        return TruthSnapshot(seed=session.seed, nodes=nodes, passages=passages,
                             deposit=(deposit.x, deposit.y),
                             agent=session.world.position(),
                             trail=list(session.truth_trail),
                             misturns=session.misturns)
