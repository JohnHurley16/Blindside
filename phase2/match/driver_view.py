"""The narrow face of a Session that a demonstration is handed."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..demo.stop_view import StopView
from ..eval.run_outcome import RunOutcome

if TYPE_CHECKING:
    from .session import Session


class DriverView:
    """`demo.run_driver.RunDriver` over a Session, and nothing else.

    A Session holds World. A demonstration keeps its driver for the whole run, so
    handed the Session itself it would have `driver.world` one attribute away,
    with no import for the invariant check to see. This object carries the
    protocol's members only. Python cannot stop reflection; this removes the
    route that needs none.
    """

    def __init__(self, session: Session) -> None:
        self.__session = session
        self.seed: int = session.seed
        self.enabled_predicates: list[str] = list(session.enabled_predicates)
        self.enabled_actions: list[str] = list(session.enabled_actions)
        self.params: dict[str, dict[str, float]] = {p: dict(v) for p, v in session.params.items()}

    @property
    def outcome(self) -> RunOutcome | None:
        return self.__session.outcome

    def advance_to_stop(self) -> StopView | None:
        return self.__session.advance_to_stop()

    def choose(self, action: str) -> bool:
        return self.__session.choose(action)
