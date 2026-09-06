"""Oscillator shapes available to a voice."""
from __future__ import annotations

from enum import StrEnum


class Waveform(StrEnum):
    SINE = "sine"
    SAW = "saw"
    SQUARE = "square"
    NOISE = "noise"
