"""What answers a stop: a callable from a StopView to an action id."""
from __future__ import annotations

from typing import Callable

from ..policy.stop_view import StopView

Chooser = Callable[[StopView], str]
