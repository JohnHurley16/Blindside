"""The truth camera's subject, chosen every frame from a fixed priority list.

SPECTATOR-DISPLAY.md section 7.2. This is the answer to the one thing the feasibility
spike said does not fit: at whole-cave framing a machine is about nine logical pixels
and vanishes against the rock, so the target beat renders as a red disc with nothing
legible on it. The answer to an invisible subject is to move the camera to it, not to
inflate the glyph -- and a `center` lerp costs 0.3 ms.

Four of the eleven rules are load-bearing:

  1  produces the target beat at 5:32 with nothing scripted -- the warning arms while
     the player is at 11.5 cells and the camera stays on the machinery to 5:58.6.
  4  is the echo, and the only rule that points the camera at nothing: the scripted
     ping is born in a labelled dead end fifty cells from anything, and its entire
     meaning is that there is nothing there. No second rule may promote a sound; a
     camera that chases every ping shows nothing.
  8  fixes the 236-second fix drought: the player is doing nothing worth a close shot
     and the rival is walking to the machinery, so cut to the thing that is happening.
 10  draws the heartbeat. Placed this low it takes the camera only when the match has
     nothing else, which in this seed is the three empty windows -- so the rule is
     learned three times for free before it ever costs anything.

The dwell is overridden by a MAJOR event. The ease never is: the director does not cut.
"""
from __future__ import annotations

import dataclasses
import math

from .. import tuning as T
from ..match.stage_frame import StageFrame, StageMachine
from .shot import Shot

DEATH_HOLD_S: float = 8.0        # section 7.2 rule 2
BEACON_HOLD_S: float = 6.0       # rule 3
EXTRACTION_HOLD_S: float = 12.0  # rule 7: long enough to read the distance home
SOUND_HOLD_S: float = 4.0        # rule 4
JAM_MULTIPLIER: float = 4.0      # rule 9: sixteen seconds, because four is a manoeuvre
GLYPH_HALF: float = T.GLYPH_LENGTH_CELLS * 0.5     # a machine is a subject with a size


class Director:
    """Holds the camera. `vertical_fraction` is how much of the framed width fits in
    the rectangle's height, which is a property of the slot rather than of the scene --
    so the same shot opens wider in a squatter rectangle instead of cropping."""

    def __init__(self, vertical_fraction: float) -> None:
        self.vertical_fraction: float = vertical_fraction
        self.cx: float = 100.0
        self.cy: float = 60.0
        self.cells: float = T.CAMERA_WIDE_CELLS
        self._vx: float = 0.0
        self._vy: float = 0.0
        self._vc: float = 0.0
        self._shot: Shot | None = None
        self._since: float = 0.0
        self._died_at: dict[str, float] = {}
        self._died_where: dict[str, tuple[float, float]] = {}
        self._beacon_moved_at: float | None = None
        self._beacon_moved_to: tuple[float, float] = (0.0, 0.0)
        self._sound_at: float | None = None
        self._sound_where: tuple[float, float] = (0.0, 0.0)
        self._seeded: bool = False

    # ---- one frame -------------------------------------------------------------------
    def update(self, frame: StageFrame, dt: float, fix_easing: bool) -> None:
        self._latch(frame)
        want = self._choose(frame, fix_easing)
        first = self._shot is None
        changing = first or want.key != self._shot.key
        if changing and (first or want.major
                         or frame.t - self._since >= T.CAMERA_MIN_DWELL_S):
            self._shot = want
            self._since = frame.t
        elif not changing:
            self._shot = want                       # same subject, and it has moved
        else:
            # The dwell is blocking a change of subject, so keep following the one the
            # camera already has. Holding its last position instead would freeze the
            # frame while the machine in it walked out of the shot.
            self._shot = self._refresh(self._shot, frame)
        assert self._shot is not None
        self._ease(self._shot, dt)

    def _refresh(self, shot: Shot, frame: StageFrame) -> Shot:
        if shot.key.startswith("player"):
            return dataclasses.replace(shot, cx=frame.player.x, cy=frame.player.y)
        if shot.key == "rival-working":
            return dataclasses.replace(shot, cx=frame.rival.x, cy=frame.rival.y)
        if shot.key.startswith("hazard"):
            return dataclasses.replace(shot, cx=frame.ancient.x, cy=frame.ancient.y)
        if shot.key == "player-and-home":
            return shot                             # the two ends of the question
        if shot.key.startswith("both"):
            cx, cy = _midpoint(frame.player, frame.rival)
            return dataclasses.replace(shot, cx=cx, cy=cy)
        return shot                                 # a wreck, an echo: a fixed place

    def _ease(self, target: Shot, dt: float) -> None:
        """Critically damped, `CAMERA_EASE_S` to settle. A camera that is always
        drifting is a camera the viewer stops trusting, so this never cuts and the
        dwell above means it changes subject at most once every six seconds."""
        omega = 4.0 / max(T.CAMERA_EASE_S, 1e-3)
        self.cx, self._vx = _spring(self.cx, self._vx, target.cx, omega, dt)
        self.cy, self._vy = _spring(self.cy, self._vy, target.cy, omega, dt)
        self.cells, self._vc = _spring(self.cells, self._vc, target.cells, omega, dt)

    # ---- what happened, remembered long enough to be worth a shot ----------------------
    def _latch(self, frame: StageFrame) -> None:
        """On the first frame it sees, the director notes what has *already* happened
        without dating it. Otherwise a `--snap` at 5:46 opens on the beacon that moved
        at 2:21, because to a camera that has watched nothing everything is news."""
        old = frame.t - 1e6 if not self._seeded else frame.t
        for name, machine in (("player", frame.player), ("rival", frame.rival)):
            if not machine.alive and name not in self._died_at:
                self._died_at[name] = old
                self._died_where[name] = (machine.x, machine.y)
        for beacon in frame.beacons:
            if beacon.moved_from is not None and self._beacon_moved_at is None:
                self._beacon_moved_at = old
                self._beacon_moved_to = (beacon.x, beacon.y)
        if self._seeded:
            for sound in frame.born:
                far = min(math.hypot(sound.x - m.x, sound.y - m.y)
                          for m in (frame.player, frame.rival))
                if far > T.CAMERA_NEAR_CELLS:
                    self._sound_at = frame.t
                    self._sound_where = (sound.x, sound.y)
        self._seeded = True

    # ---- the priority list --------------------------------------------------------------
    def _choose(self, frame: StageFrame, fix_easing: bool) -> Shot:
        a = frame.ancient
        player, rival = frame.player, frame.rival
        counting = a.signature_strength > 0.0 or a.is_lethal

        # 1 -- a machine is at the machinery while it counts. The target beat.
        if counting:
            watch = [m for m in (player, rival) if m.alive and
                     math.hypot(m.x - a.x, m.y - a.y) <= a.radius + T.CAMERA_HAZARD_WATCH_CELLS]
            if watch:
                return self._hold((a.x, a.y), [(m.x, m.y, GLYPH_HALF) for m in watch]
                                  + [(a.x, a.y, a.radius)], "hazard-machine")

        # 2 -- a wreck, for eight seconds. It is a MAJOR event, so it takes the camera.
        for name, when in self._died_at.items():
            if frame.t - when <= DEATH_HOLD_S:
                wx, wy = self._died_where[name]
                return Shot(wx, wy, T.CAMERA_CLOSE_CELLS, f"wreck-{name}", major=True)

        # 3 -- the spoof arming, or the beacon that just moved
        if self._beacon_moved_at is not None and frame.t - self._beacon_moved_at <= BEACON_HOLD_S:
            bx, by = self._beacon_moved_to
            return self._hold(((player.x + bx) / 2.0, (player.y + by) / 2.0),
                              [(player.x, player.y, GLYPH_HALF), (bx, by, GLYPH_HALF)],
                              "beacon-moved", major=True)
        if frame.spoof_arming > 0.0:
            return Shot(player.x, player.y, T.CAMERA_CLOSE_CELLS, "player-arming")

        # 4 -- a sound with no source. The echo, and nothing else in this match.
        if self._sound_at is not None and frame.t - self._sound_at <= SOUND_HOLD_S:
            sx, sy = self._sound_where
            return Shot(sx, sy, T.CAMERA_CLOSE_CELLS, "sound", major=True)

        # 5 -- two machines close enough to be one shot
        if player.alive and rival.alive:
            gap = math.hypot(player.x - rival.x, player.y - rival.y)
            if gap <= T.CAMERA_NEAR_CELLS:
                return self._hold(((player.x + rival.x) / 2.0, (player.y + rival.y) / 2.0),
                                  [(player.x, player.y, GLYPH_HALF),
                                   (rival.x, rival.y, GLYPH_HALF)], "both-close")

        # 6, 7 -- a fix landing, a load, the extraction window opening
        if fix_easing:
            return Shot(player.x, player.y, T.CAMERA_CLOSE_CELLS, "player-fix")
        if player.load_progress > 0.0:
            return Shot(player.x, player.y, T.CAMERA_CLOSE_CELLS, "player-loading")
        if (T.EXTRACT_WINDOW_OPENS <= frame.t < T.EXTRACT_WINDOW_OPENS + EXTRACTION_HOLD_S
                and len(frame.trail_player)):
            # Framed to hold the machine and the shaft together, which at 6:30 is very
            # nearly WIDE -- because the question the beat asks is how far is home. The
            # shaft is the first place the trail was ever recorded.
            sx, sy = float(frame.trail_player[0][0]), float(frame.trail_player[0][1])
            return self._hold(((player.x + sx) / 2.0, (player.y + sy) / 2.0),
                              [(player.x, player.y, GLYPH_HALF), (sx, sy, GLYPH_HALF)],
                              "player-and-home")

        # 8 -- the drought. The player has held the camera and stopped; the rival has not.
        # Written against the player's own stall rather than against how long it has
        # been the subject, because the latter oscillates: cutting away resets the
        # clock, which cuts back, which is a camera that flickers every six seconds.
        if (rival.alive and player.stalled_for > T.CAMERA_MAX_HOLD_S
                and rival.stalled_for <= T.STALL_SECONDS):
            return Shot(rival.x, rival.y, T.CAMERA_CLOSE_CELLS, "rival-working")

        # 9 -- a jam, which is not a manoeuvre
        if player.stalled_for > T.STALL_SECONDS * JAM_MULTIPLIER:
            return Shot(player.x, player.y, T.CAMERA_CLOSE_CELLS, "player-jammed")

        # 10 -- the heartbeat, when the match has nothing else
        if counting:
            return self._hold((a.x, a.y), [(a.x, a.y, a.radius)], "hazard-empty")

        # 11 -- the whole cave
        return self._hold(_midpoint(player, rival),
                          [(player.x, player.y, GLYPH_HALF), (rival.x, rival.y, GLYPH_HALF)],
                          "both-wide", widest=True)

    # ---- framing ----------------------------------------------------------------------
    def _hold(self, centre: tuple[float, float],
              subjects: list[tuple[float, float, float]], key: str,
              major: bool = False, widest: bool = False) -> Shot:
        """The centre is never shifted to dodge an overlay -- shifting it moves the whole
        world under the viewer -- so when a subject would fall outside, the scale opens
        instead, which only ever zooms out. Capped at WIDE."""
        cx, cy = centre
        half_w = max(abs(x - cx) + r for x, y, r in subjects)
        half_h = max(abs(y - cy) + r for x, y, r in subjects)
        # 2.5 rather than 2.0, so a subject sits inside 80% of the half-frame rather
        # than on its edge. Measured: at 5:32 the player is 10.3 cells from the
        # machinery and a 40-cell frame is 10.75 cells of half-height, which puts the
        # nose of a 2.4-cell glyph over the edge. It opens the target beat to 44.1
        # cells, which is 28.4 px per cell and a 68 px machine, against the 40 cells
        # section 5.1 assumed.
        needed = max(2.5 * half_w, 2.5 * half_h / max(self.vertical_fraction, 1e-3))
        floor = T.CAMERA_WIDE_CELLS if widest else T.CAMERA_CLOSE_CELLS
        return Shot(cx, cy, min(max(floor, needed), T.CAMERA_WIDE_CELLS), key, major)


def _midpoint(a: StageMachine, b: StageMachine) -> tuple[float, float]:
    return ((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)


def _spring(x: float, v: float, target: float, omega: float, dt: float) -> tuple[float, float]:
    """Closed form, not a Euler step, so it is exact and stable at any dt.

    That matters twice over: a --snap frame advances the match by minutes between
    draws and must land on the shot rather than a twentieth of the way to it, and a
    recorder frame is a twentieth of a second of sim time however long it took to draw.
    """
    if dt <= 0.0:
        return x, v
    decay = math.exp(-omega * dt)
    offset = x - target
    slope = v + omega * offset
    return target + (offset + slope * dt) * decay, (slope - omega * (offset + slope * dt)) * decay
