"""What a policy is currently doing."""
from __future__ import annotations

from enum import StrEnum


class PolicyMode(StrEnum):
    TRAVEL = "travel"   # running the survey route
    LOAD = "load"       # sitting at what it believes is a deposit
    HOME = "home"       # retracing the believed beacon chain to the shaft
    SEARCH = "search"   # at the believed shaft, but nothing is answering
