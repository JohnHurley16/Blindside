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
    damage: float                          # 0..1 of ground shock taken, monotone. Truth:
                                           # the machine itself is not told this number in
                                           # Phase 1, and no predicate reads it. Phase 3's
                                           # Return::SelfReport is where the agent learns
                                           # it, through a sensor, so it can be wrong.


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
    """The Assayer, as much of it as a screen is allowed to know.

    `radius` is the nine-cell disc the camera and the zone flag still use; the shape
    that actually hurts is in `coupling`, which is not a circle. `phase` is an
    `AncientPhase` member's plain string value, for the same reason `StageSound`
    carries one: a StageFrame may not carry a type from anywhere else.
    """

    x: float
    y: float
    radius: float
    signature_strength: float
    seconds_until_lethal: float
    is_lethal: bool
    bearing_deg: float                     # where the array points now, swinging through
                                           # the slew: the tell, seventeen seconds early
    phase: str                             # listening | slew | locked | wind | firing | lethal
    phase_progress: float                  # 0..1 through that phase; across the wind it is
                                           # the nine clicks of the winch taking load
    is_slewing: bool
    coupling: np.ndarray                   # (120, 200) float64. gain(theta) * (9/d)^2 at
                                           # every cell: 1.0 is the lethal contour, 0.25 the
                                           # felt one. Lopsided toward the water, because a
                                           # flooded working carries the shock much further


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
