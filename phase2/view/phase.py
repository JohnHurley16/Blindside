"""Where the session has got to. One name per thing the window is showing."""
from __future__ import annotations

from enum import Enum


class Phase(str, Enum):
    """The staged tutorial, then the induction, then the correction loop."""
    STOP = "stop"                # a run is waiting for a decision
    RUN_OVER = "run over"        # the run ended; the reveal is up
    INDUCED = "induced"          # the tree and the sentence are up
    GHOST = "ghost"              # the induced tree has been run beside a demonstration
    SCRUB = "scrub"              # picking the stop to take over from
    TAKEOVER = "takeover"        # choosing again from that stop
    PROMOTED = "promoted"        # the suffix was replaced and the tree induced again
    DONE = "done"
