"""Belief-only rendering. Truth is drawn once, after the match is over."""
from __future__ import annotations

from .backend import pick_backend
from .view import View

__all__ = ["View", "pick_backend"]
