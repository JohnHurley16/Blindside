"""What the near-field sense shows when the agent stops."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class JunctionReturn:
    """The passage mouths around the agent, as bearings in its own body frame.

    Every mouth is listed, the one it came in by included -- the sense does not
    know which is which. Nothing further along any of them is seen.
    """
    bearings_body: tuple[float, ...]
