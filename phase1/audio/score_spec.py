"""The score, parsed. Nothing in this file decides anything about the music.

The music lives in a JSON document -- `spikes/score/trailer.json` -- and this is the reader
for it. The split is the whole point of the exercise: changing a note must not mean editing
the engine, so every pitch, every entry, every level and every room setting is a number in
that file and the only thing here is the grammar those numbers are written in.

The grammar is one idea repeated. A SECTION is a span of the trailer. A LINE is one voice of
the score inside a section: a timbre, a pitch, a level, a room, and how often it strikes. A
pad is a line that strikes every nine seconds and rings for fifteen; the pulse is the same
line striking every second and ringing for a third of one. There is no separate pad type and
no separate pulse type, which is why the transport is short.

Unknown keys are an error rather than a shrug. This document is meant to be hand-edited and
a silently ignored misspelling of `duration_s` is a note that does not sound with no way to
find out why.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_LINE_KEYS: frozenset[str] = frozenset({
    "id", "timbre", "pitch", "glide_to", "detune_cents", "pan", "quality", "quality_to",
    "amp", "amp_to", "attack_s", "duration_s", "decay_s", "every_s", "at_s", "until_s",
    "accent_every", "accent_amp", "max_reflections", "note"})
_SECTION_KEYS: frozenset[str] = frozenset({"id", "from_s", "to_s", "note", "lines"})
_TIMBRE_KEYS: frozenset[str] = frozenset({"ratios", "tilt", "noise_lowpass", "note"})
_ROOT_KEYS: frozenset[str] = frozenset({
    "name", "note", "sample_rate", "length_s", "block_samples", "stop", "timbres",
    "pitches", "sections"})


class ScoreError(ValueError):
    """A score document that cannot be played, with the offending key named."""


def _check(keys: Any, allowed: frozenset[str], where: str) -> None:
    unknown = sorted(set(keys) - allowed)
    if unknown:
        raise ScoreError(f"{where}: unknown key(s) {unknown}; allowed {sorted(allowed)}")


@dataclass(frozen=True, slots=True)
class Timbre:
    """What a struck thing is made of.

    `ratios` are multiples of the fundamental and are deliberately NOT integers: a bar rings
    at 1, 2.09, 3.42 and that inharmonicity is the difference between metal and an organ.
    They are also the score's whole register discipline, because a ratio times a fundamental
    is where the energy actually lands -- see `Score.band_report`.
    """
    name: str
    ratios: tuple[float, ...]
    tilt: float
    noise_lowpass: int          # 0 means tonal; anything else is a band-limited stroke

    @property
    def tonal(self) -> bool:
        return self.noise_lowpass == 0


@dataclass(frozen=True, slots=True)
class Line:
    """One voice of the score inside one section."""
    id: str
    timbre: str
    pitch: float                # Hz, already resolved through `pitches` and detuned
    glide_to: float             # equal to pitch unless the note bends
    pan: float
    quality: float
    quality_to: float
    amp: float
    amp_to: float
    attack_s: float
    duration_s: float
    decay_s: float
    every_s: float              # 0.0 -> a single strike at `at_s`
    at_s: float                 # seconds after the section starts
    until_s: float              # seconds after the section starts; inf for "to the end"
    accent_every: int
    accent_amp: float
    max_reflections: int


@dataclass(frozen=True, slots=True)
class Section:
    id: str
    from_s: float
    to_s: float
    lines: tuple[Line, ...] = field(default_factory=tuple)

    @property
    def span(self) -> float:
        return max(self.to_s - self.from_s, 1e-6)


@dataclass(frozen=True, slots=True)
class ScoreSpec:
    name: str
    sample_rate: int
    length_s: float
    block_samples: int
    stop_s: float               # the hard cut; inf for a score that never stops
    stop_ramp_s: float
    timbres: dict[str, Timbre]
    sections: tuple[Section, ...]

    @staticmethod
    def load(path: str | Path) -> ScoreSpec:
        return ScoreSpec.parse(json.loads(Path(path).read_text(encoding="utf-8")), str(path))

    @staticmethod
    def parse(doc: dict[str, Any], where: str = "<score>") -> ScoreSpec:
        _check(doc.keys(), _ROOT_KEYS, where)
        pitches: dict[str, float] = {k: float(v) for k, v in doc.get("pitches", {}).items()}
        timbres: dict[str, Timbre] = {}
        for name, raw in doc.get("timbres", {}).items():
            _check(raw.keys(), _TIMBRE_KEYS, f"{where}: timbre {name!r}")
            ratios = tuple(float(r) for r in raw["ratios"])
            if not ratios or ratios[0] != 1.0:
                raise ScoreError(f"{where}: timbre {name!r} must start at ratio 1.0")
            timbres[name] = Timbre(name=name, ratios=ratios,
                                   tilt=float(raw.get("tilt", 1.4)),
                                   noise_lowpass=int(raw.get("noise_lowpass", 0)))

        sections: list[Section] = []
        for raw_section in doc.get("sections", []):
            _check(raw_section.keys(), _SECTION_KEYS, f"{where}: section")
            sid = str(raw_section["id"])
            from_s, to_s = float(raw_section["from_s"]), float(raw_section["to_s"])
            if to_s <= from_s:
                raise ScoreError(f"{where}: section {sid!r} ends before it starts")
            lines: list[Line] = []
            for raw_line in raw_section.get("lines", []):
                _check(raw_line.keys(), _LINE_KEYS, f"{where}: {sid}")
                lines.append(_line(raw_line, sid, pitches, timbres, where))
            sections.append(Section(id=sid, from_s=from_s, to_s=to_s, lines=tuple(lines)))
        sections.sort(key=lambda s: s.from_s)

        stop = doc.get("stop") or {}
        return ScoreSpec(
            name=str(doc.get("name", "score")),
            sample_rate=int(doc.get("sample_rate", 48000)),
            length_s=float(doc.get("length_s", 120.0)),
            block_samples=int(doc.get("block_samples", 480)),
            stop_s=float(stop.get("t_s", math.inf)),
            stop_ramp_s=float(stop.get("ramp_s", 0.008)),
            timbres=timbres,
            sections=tuple(sections))


def _hz(value: Any, pitches: dict[str, float], where: str) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if value in pitches:
        return pitches[str(value)]
    raise ScoreError(f"{where}: pitch {value!r} is neither a number nor a name in `pitches`")


def _line(raw: dict[str, Any], section_id: str, pitches: dict[str, float],
          timbres: dict[str, Timbre], where: str) -> Line:
    line_id = str(raw.get("id", "line"))
    tag = f"{where}: {section_id}/{line_id}"
    timbre = str(raw["timbre"])
    if timbre not in timbres:
        raise ScoreError(f"{tag}: timbre {timbre!r} is not in `timbres`")
    bend = 2.0 ** (float(raw.get("detune_cents", 0.0)) / 1200.0)
    pitch = _hz(raw["pitch"], pitches, tag) * bend
    glide = _hz(raw["glide_to"], pitches, tag) * bend if raw.get("glide_to") else pitch
    amp = float(raw["amp"])
    quality = float(raw.get("quality", 0.35))
    duration = float(raw["duration_s"])
    return Line(
        id=f"{section_id}/{line_id}", timbre=timbre, pitch=pitch, glide_to=glide,
        pan=float(raw.get("pan", 0.0)), quality=quality,
        quality_to=float(raw.get("quality_to", quality)),
        amp=amp, amp_to=float(raw.get("amp_to", amp)),
        attack_s=float(raw.get("attack_s", 0.02)),
        duration_s=duration,
        decay_s=float(raw.get("decay_s", duration * 0.5)),
        every_s=float(raw.get("every_s", 0.0)),
        at_s=float(raw.get("at_s", 0.0)),
        until_s=float(raw["until_s"]) if "until_s" in raw else math.inf,
        accent_every=int(raw.get("accent_every", 0)),
        accent_amp=float(raw.get("accent_amp", 1.0)),
        max_reflections=int(raw.get("max_reflections", 2)))
