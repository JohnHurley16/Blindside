"""One thing that happened, placed on the timeline."""
from __future__ import annotations

from dataclasses import dataclass

from .event_kind import EventKind


@dataclass(slots=True, frozen=True)
class MatchEvent:
    """A moment worth marking.

    These are not captions any more. Floating text over the map asked the viewer to
    read while they were trying to look; on a timeline the same information has a
    position, so the shape of the match is visible at a glance and the words only
    have to be read for the one event happening now.
    """
    t: float
    text: str
    detail: str = ""
    kind: EventKind = EventKind.CONTACT
    major: bool = False
