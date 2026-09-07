"""The truth channel's payload: one frozen record of numbers, per frame.

SPECTATOR-DISPLAY.md section 4.1. Nothing in here is a `World`, an `AgentTruth`, an
`Ancient` or a `Beacon`; nothing in here has a method or a callable; every array is a
copy with `writeable = False`. There is no route from a StageFrame back into truth,
which is what lets the renderer hold one every frame.

`match/invariant.py` rule 7 walks this module and fails if any dataclass here is not
`frozen=True, slots=True`, or if any field is annotated with anything but a plain
type, an ndarray, `None`, or another dataclass declared here -- so a future "just pass
the World through" fails at the declaration rather than at runtime.

Deliberately shaped like Phase 5's `ReplayFrame` (BLD-76, BLD-145) at a tenth of the
scale, so that one does not have to be improvised later.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class StageMachine:
    """One machine as it really is."""

    x: float
    y: float
    heading: float
    alive: bool
    cargo: int
    load_progress: float
    stalled_for: float
    in_ancient: bool


@dataclass(frozen=True, slots=True)
class StageBeacon:
    """A transponder at its true position. `moved_from` is where it used to be, and is
    None until the rival relocates it -- the surprise is preserved because nothing here
    marks a beacon as a lie before it becomes one."""

    x: float
    y: float
    owner: str
    moved_from: tuple[float, float] | None


@dataclass(frozen=True, slots=True)
class StageAncient:
    """The machinery. `seconds_until_lethal` has never been drawn in this project."""

    x: float
    y: float
    radius: float
    signature_strength: float
    seconds_until_lethal: float
    is_lethal: bool


@dataclass(frozen=True, slots=True)
class StageDeposit:
    x: float
    y: float
    radius: float


@dataclass(frozen=True, slots=True)
class StageSound:
    """A sound born this frame, at its true origin. `character` is the enum's value, a
    plain string, because a StageFrame may not carry a type from anywhere else."""

    x: float
    y: float
    character: str


@dataclass(frozen=True, slots=True)
class StageFrame:
    """Everything the spectator screen is allowed to know about the world."""

    t: float
    grid: np.ndarray                       # (120, 200) uint8; 0 rock, 1 dry, 2 flooded
    player: StageMachine
    rival: StageMachine
    trail_player: np.ndarray               # (n, 3) of x, y, t
    trail_rival: np.ndarray
    beacons: tuple[StageBeacon, ...]
    ancient: StageAncient
    deposits: tuple[StageDeposit, ...]
    born: tuple[StageSound, ...]
    error_cells: float                     # how wrong the player's belief is, in truth
    heading_error_deg: float
    spoof_arming: float                    # 0..1, closing on the lie
    seconds_home: float                    # true walking time home, over WALKABLE
    error_history: np.ndarray              # (n, 3) of t, error_cells, sigma, at 2 Hz
