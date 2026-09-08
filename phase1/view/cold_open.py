"""Twenty-one words, six seconds, before the clock starts.

SPECTATOR-DISPLAY.md 3, 5 and 7.5. The gate viewer was lost at 0:00 and stayed lost, and
the design panel's stranger-judge called this the cheapest thing on the table -- three of
the four proposals had skipped it. What she needed was five facts:

    nobody is driving it        no radio.
    it cannot be told anything  you cannot drive it.
    what it is there to do      it must bring two loads home
    how long it has             in eight minutes.
    you have one command        you can call it back once.

That is the whole card. **No paragraph, no tutorial, no legend, and no vocabulary**: every
word of it is a word a stranger already owns, and nothing on the card names anything on the
screen. It is deliberately not a key -- a key teaches the display, and the display is
supposed to teach itself.

**It is wordless-adjacent because the picture is doing half of it.** Under the words the
scrim lifts and the cave comes up out of black, and the truth camera starts flat at 90
degrees and arrives at 72 over the same six seconds. The camera *arriving* is what makes a
flat plan resolve into a place, and it teaches in one move -- with no sentence about it --
that the big picture has depth and that this is somewhere rather than something.

**It is in the recorded video as well as the live window**, because the gate viewer watched
a recording and an explanation that only exists live is an explanation she never got. It is
a branch against the existing wall clock rather than a new timer -- vispy timers created
outside `__main__` fire once or never -- and `Recorder.run()` prepends `COLD_OPEN_S * fps`
frames and drives it directly.

**Everything else on the screen is put away while it runs**, and it takes two mechanisms
because a scrim cannot do it alone. The rail's two numbers reading `0` and `0` under a
title card would be the first thing a stranger tried to interpret and they mean nothing
yet, so `TextGroup.mute` blanks every chrome string except these five. Everything that is
not a string -- the panel grounds, the rail's separators, the damage bar, the timeline's
pips, the inset and the minimap -- is hidden outright by the curtain, and its visibility is
put back exactly as it was found.

The scrim is then only over **the main view**, which is what leaves it free to lift early:
the cave has to come up *under* the words rather than after them, and a full-canvas scrim
at the alpha that does that would also bring up a magenta timeline pip and a red damage
bar at forty-five per cent, which is not "black" by any reading of the beat sheet.
"""
from __future__ import annotations

import numpy as np
from vispy.scene import visuals
from vispy.visuals.transforms import STTransform

from .. import tuning as T
from . import palette
from .text_group import DISPLAY, Slot, TextGroup

# Each line carries its own colour, because one of them has to. A verifier watching the
# finished video said it knew what the machine was for and never learnt WHICH MACHINE WAS
# ITS OWN -- it worked that out minutes later from the rail reading "IT IS CARRYING". So
# the line that says so is drawn in the exact colour the machine is drawn in, and the one
# about the other machine in the other machine's colour: the card teaches the two hues it
# is about to rely on for eight minutes, without a legend and without naming a colour.
LINES: tuple[tuple[str, palette.Rgb], ...] = (
    ("no radio.", palette.PRIMARY),
    ("you cannot drive it.", palette.PRIMARY),
    ("the pale one is yours.", palette.BONE),
    ("the orange one is not.", palette.EMBER),
    ("it must bring two loads home", palette.PRIMARY),
    ("in eight minutes.", palette.PRIMARY),
    ("you can call it back once.", palette.PRIMARY),
)


class ColdOpen:
    """The card, the scrim under it, and the camera's descent."""

    def __init__(self, group: TextGroup, parent: object, curtain: tuple[object, ...] = (),
                 order: int = 0) -> None:
        self.group: TextGroup = group
        self.curtain: tuple[object, ...] = curtain
        self._was_visible: tuple[bool, ...] = ()
        self.slots: tuple[Slot, ...] = tuple(
            group.slot(DISPLAY, line, rgb=hue, alpha=0.0) for line, hue in LINES)

        # An Image, not a Rectangle: setting any property on a Rectangle regenerates its
        # geometry and forces a synchronous repaint, and this one changes every frame for
        # six seconds. One texel, stretched by a transform, uploaded from a preallocated
        # same-shaped array so the texture is never reallocated.
        self._pixel: np.ndarray = np.zeros((1, 1, 4), dtype=np.float32)
        self._pixel[0, 0, :3] = palette.VOID
        # Starts clear and hidden, not black: `--snap` at a match time and the recorder's
        # own frames both build a View that never drives the cold open at all, and a scrim
        # that defaults to opaque would make every one of those frames a black rectangle.
        self._pixel[0, 0, 3] = 0.0
        self.scrim = visuals.Image(self._pixel, parent=parent, interpolation="nearest")
        self.scrim.set_gl_state("translucent", depth_test=False)
        self.scrim.order = order
        self.scrim.visible = False
        self.scrim.transform = STTransform(scale=(1.0, 1.0, 1.0))

        self._alpha: float = -1.0
        # Two flags, not one, and the distinction is load-bearing. `showing` is whether the
        # card is up *right now* -- what the curtain and the mute hang off. `done` is
        # whether it has finished, which is what stops a second run. A single `running`
        # flag initialised to True made every `--snap` at a match time draw with the
        # curtain down, because a View that never drives the card had never cleared it.
        self.showing: bool = False
        self.done: bool = False

    # ---- geometry --------------------------------------------------------------------
    def move(self, w: float, h: float, main: tuple[float, float, float, float]) -> None:
        """Everything positional is derived from the *live* canvas size: `show()` clamps
        the canvas to the screen and `render()` does not, so the window and the mp4 are
        different sizes and a card centred by eye in one is off-centre in the other."""
        main_x, main_y, main_w, main_h = main
        self.scrim.transform = STTransform(scale=(main_w, main_h, 1.0),
                                           translate=(main_x, main_y, 0.0))
        block = T.COLD_OPEN_LINE_H * (len(LINES) - 1)
        x = main_x + main_w * 0.10
        top = main_y + (main_h - block) * 0.5
        for index, slot in enumerate(self.slots):
            slot.at(x, top + index * T.COLD_OPEN_LINE_H)

    # ---- one frame -------------------------------------------------------------------
    def update(self, elapsed: float) -> bool:
        """`elapsed` is presentation time: wall seconds since the first frame, which is
        `COLD_OPEN_S` ahead of match time for the whole match. Returns whether it is still
        running, which is what holds the sim at t = 0."""
        if self.done:
            return False
        running = elapsed < T.COLD_OPEN_S
        if running and not self.showing:
            self.group.mute(exempt=self.slots)
            self.showing = True

        out_from = T.COLD_OPEN_S - T.COLD_OPEN_FADE_S
        out = _ramp(elapsed, out_from, T.COLD_OPEN_S)          # 0 while up, 1 when gone
        for index, (slot, hue) in enumerate(zip(self.slots, (h for _, h in LINES))):
            arrive = _ramp(elapsed, index * T.COLD_OPEN_LINE_S,
                           index * T.COLD_OPEN_LINE_S + T.COLD_OPEN_LINE_IN_S)
            # The line's own colour, not PRIMARY: two of them are the machines' hues and
            # tinting everything white here is what threw that away.
            slot.tint(hue, round(arrive * (1.0 - out), 2))

        settled = T.COLD_OPEN_SCRIM_HOLD + (1.0 - T.COLD_OPEN_SCRIM_HOLD) * (
            1.0 - _smooth(_ramp(elapsed, 0.0, T.COLD_OPEN_SCRIM_S)))
        alpha = round(settled * (1.0 - _smooth(out)), 3)
        if alpha != self._alpha:
            self._alpha = alpha
            self._pixel[0, 0, 3] = alpha
            self.scrim.set_data(self._pixel)
        if self.scrim.visible is not (alpha > 0.0):
            self.scrim.visible = alpha > 0.0

        if not running:
            if self.showing:
                # Before the frame's own assignments, so a dynamic string restored here is
                # immediately overwritten with the value this frame actually wants.
                self.group.unmute()
                for node, was in zip(self.curtain, self._was_visible):
                    node.visible = was
                self.showing = False
            self.done = True
        return running

    def hold(self) -> None:
        """Take the curtain down, at the END of a frame -- and record what it covered.

        Both halves have to happen here rather than in `update`, which runs first.
        `StatusPanel.set_bars` and the timeline re-show their own visuals from inside
        `draw()`, and `draw()` runs under the card exactly as it runs under the match, so
        hiding them before that leaves a white damage bar across the middle of a title
        card. And the state to *restore* is the state after a frame has drawn, not the
        constructor's: capturing before the first draw recorded a damage bar that had not
        been shown yet, and put it back hidden for the rest of the match.
        """
        if not self._was_visible:
            self._was_visible = tuple(bool(node.visible) for node in self.curtain)
        for node in self.curtain:
            if node.visible:
                node.visible = False

    def elevation(self, elapsed: float) -> float:
        """The camera's descent, 90 degrees to 72, over the whole six seconds."""
        return (T.COLD_OPEN_FROM_DEG + (T.ELEVATION_DEFAULT_DEG - T.COLD_OPEN_FROM_DEG)
                * _smooth(_ramp(elapsed, 0.0, T.COLD_OPEN_S)))


def _ramp(x: float, a: float, b: float) -> float:
    return min(max((x - a) / max(b - a, 1e-6), 0.0), 1.0)


def _smooth(k: float) -> float:
    return k * k * (3.0 - 2.0 * k)
