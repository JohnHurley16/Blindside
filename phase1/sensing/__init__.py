"""The sensor layer: the only place where truth becomes belief.

`SensorRig` is the single class permitted to read `phase1.truth`. Everything it
emits is a return, and returns are the only thing `phase1.belief` consumes.
"""
from __future__ import annotations

from .sensor_rig import SensorRig
from .sound_field import SoundField

__all__ = ["SensorRig", "SoundField"]
