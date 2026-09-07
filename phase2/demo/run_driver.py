"""The narrow face of a run that a demonstration is allowed to see."""
from __future__ import annotations

from typing import Protocol

from ..eval.run_outcome import RunOutcome
from .stop_view import StopView


class RunDriver(Protocol):
    """Stops in, actions out. Nothing about the world crosses this."""

    seed: int
    enabled_predicates: list[str]
    enabled_actions: list[str]
    params: dict[str, dict[str, float]]
    outcome: RunOutcome | None

    def advance_to_stop(self) -> StopView | None: ...

    def choose(self, action: str) -> bool: ...


def members() -> frozenset[str]:
    """The public names the protocol declares, read off the protocol itself so
    there is one list and not two."""
    return frozenset(RunDriver.__annotations__) | frozenset(
        name for name in vars(RunDriver) if not name.startswith("_")
    )


def assert_narrow(driver: object) -> None:
    """Refuse a driver that offers more than the protocol.

    A duck type is not a boundary: the object that satisfies this protocol most
    easily is `match.session.Session`, which holds World, and a demonstration
    keeps its driver for the whole run. Handing it the Session would put ground
    truth one plain attribute access away with no import for the invariant check
    to find. `match.driver_view.DriverView` is the object meant to be passed;
    this is the check that says so at the point it matters.
    """
    extra = sorted(name for name in dir(driver)
                   if not name.startswith("_") and name not in members())
    if extra:
        raise TypeError(
            f"a demonstration's driver may offer only {sorted(members())}; "
            f"{type(driver).__name__} also offers {extra}"
        )
