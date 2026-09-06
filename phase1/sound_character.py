"""What a sound is *like*, which is not the same as what made it.

Shared vocabulary between the sensor layer and Belief. Deliberately not an
identity: a contact is an unresolved detection, and the glossary is strict about
that. An agent can tell a sharp transient from a rising drone because those are
properties of the signal it received. It cannot tell a rival from an echo.
"""
from __future__ import annotations

from enum import StrEnum


class SoundCharacter(StrEnum):
    PING = "ping"            # a sharp transient: someone's active sonar, or its echo
    TONE = "tone"            # irregular low scraping: something moving
    SIGNATURE = "signature"  # a rising drone: the ancient system winding up
    CRASH = "crash"          # a single loud event: something died
