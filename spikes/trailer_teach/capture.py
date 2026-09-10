"""Capture the trailer's teaching act (shots 8-12) off the Phase 1 teach window.

Read-only on phase1/: this builds the same objects `python -m phase1 --teach` builds
and drives them the way `_snap_stops` does -- `advance_to_stop`, `press`, `draw`,
`canvas.render()` -- but on a fixed 1/24 s clock instead of the wall clock, so the
performance is deterministic and can be shot again.

Nothing here touches World. The teach view is belief-only by construction (`Sim`
with stage=False); the spectator pass for shots 11 and 12 is the same one `--tree`
opens.

Output: spikes/trailer_teach/raw/<shot>/NNN.png at the render resolution. Framing,
the over-the-shoulder treatment and the grade are grade.py's job.
"""
from __future__ import annotations

import argparse
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from vispy import scene                                    # noqa: E402

from phase1 import tuning as T                             # noqa: E402
from phase1.demo.tree_chooser import TreeChooser           # noqa: E402
from phase1.match.match_view import MatchView              # noqa: E402
from phase1.match.run_factory import RunFactory            # noqa: E402
from phase1.match.sim import Sim                           # noqa: E402
from phase1.policy.block_registry import BlockRegistry     # noqa: E402
from phase1.policy.decision_tree import DecisionTree       # noqa: E402
from phase1.policy.run_spec import RunSpec                 # noqa: E402

FPS = 24
DT = 1.0 / FPS
SESSION = HERE / "session"
RAW = HERE / "raw"
CAUTIOUS = ROOT / "phase1" / "reference" / "cautious.json"
INDUCED = SESSION / "tree.json"
SEED = 7
# 1536 x 864 logical, times the 1.25 this display adds, is 1920 x 1080; px_scale
# multiplies that again and is the headroom the framing pass crops out of.
LOGICAL = (1536, 864)


@contextmanager
def px_scale(scale: int):
    """vispy's HiDPI multiplier, forced on every SceneCanvas built inside."""
    real = scene.SceneCanvas.__init__

    def patched(self, *a, **kw):
        kw["px_scale"] = scale
        return real(self, *a, **kw)

    scene.SceneCanvas.__init__ = patched
    try:
        yield
    finally:
        scene.SceneCanvas.__init__ = real


def teach_spec(registry: BlockRegistry, tree: DecisionTree) -> RunSpec:
    """Every block on the list, at the tree's thresholds where it has them -- what a
    player sees at the window once every block has been discovered."""
    spec = RunSpec.for_demonstration(registry, None)
    params = dict(spec.params)
    for pid, vals in tree.params.items():
        if pid in params:
            params[pid] = dict(vals)
    return RunSpec(spec.enabled_predicates, spec.enabled_actions, params)


def write(frame: np.ndarray, path: Path) -> None:
    Image.fromarray(frame[:, :, :3]).save(path, compress_level=6)


class TeachShot:
    """One take of the teaching window on a fixed clock.

    The window is built after the match has been wound, because the belief scene
    holds the `Belief` it was constructed with: a view handed a different match
    afterwards would draw the wrong map.
    """

    def __init__(self, scale: int) -> None:
        self.scale = scale
        self.registry = BlockRegistry()
        self.tree = DecisionTree.load(CAUTIOUS, self.registry)
        self.spec = teach_spec(self.registry, self.tree)
        self.chooser = TreeChooser(self.tree, self.spec)

    def key_for(self, action: str) -> str:
        return str(self.spec.enabled_actions.index(action) + 1)

    def _wound(self, stop_number: int, lead_frames: int):
        """A match answered up to the stop before `stop_number` and then walked
        forward to `lead_frames` short of the stop itself, plus that stop's own
        details, read off a throwaway match so the shot's match is never past it."""
        scout = RunFactory().open(SEED, self.spec, None)
        n = 0
        target = None
        while (stop := scout.advance_to_stop()) is not None:
            n += 1
            if n == stop_number:
                target = stop
                break
            scout.answer(self.chooser(stop))
        if target is None:
            raise SystemExit(f"the match ended before stop {stop_number}")

        shot_match = RunFactory().open(SEED, self.spec, None)
        n = 0
        while n < stop_number - 1:
            s = shot_match.advance_to_stop()
            assert s is not None
            n += 1
            shot_match.answer(self.chooser(s))
        shot_match.advance_to(target.t - lead_frames * DT)
        return shot_match, target

    def beat(self, out: Path, stop_number: int, lead_frames: int, hold_frames: int,
             tail_frames: int, index: int = 0, press: bool = True) -> int:
        """One stop, shot: `lead` frames of it still driving, the stop, `hold` frames
        of the panel waiting, the key, `tail` frames of it moving off."""
        out.mkdir(parents=True, exist_ok=True)
        match, target = self._wound(stop_number, lead_frames)
        with px_scale(self.scale):
            from phase1.view.teach_view import TeachView
            view = TeachView(match, self.registry, SESSION, show=False, size=LOGICAL)
        view.canvas.render()               # warm the shaders and the glyph atlas
        chosen = self.chooser(target)
        key = self.key_for(chosen)

        sim_t = match.t
        held = 0
        pressed = False
        total = lead_frames + hold_frames + tail_frames
        started = time.perf_counter()
        for f in range(total):
            if match.paused:
                held += 1
                if press and held > hold_frames and not pressed:
                    view.press(key)
                    pressed = True
                    sim_t = match.t
            else:
                sim_t += DT
                match.advance_to(sim_t)
                if match.paused:
                    sim_t = match.t
            view.draw()
            write(view.canvas.render(), out / f"{index + f:03d}.png")
        print(f"  stop {stop_number} at t={target.t:.2f} ({target.reason}) -> "
              f"{'key ' + key if press else 'no key'} "
              f"({self.registry.action(chosen).label}); frames "
              f"{index}..{index + total - 1}, "
              f"{(time.perf_counter() - started) / total * 1000:.0f} ms/frame")
        view.canvas.close()
        return index + total


def shot08(scale: int) -> None:
    """The panel. It has stopped. It says what it believes. Four things it could do.
    5 s: 36 frames walking in, 84 frames waiting, no key.

    Stop 6 rather than stop 5, which is the other four-action stop in this session:
    the teach window's `because:` line does not wrap and clips at the rail's right
    edge past about 28 characters, so `because: the machinery is loud` loses its last
    two letters and `because: late` does not.
    """
    out = RAW / "08_panel_stopped"
    shot = TeachShot(scale)
    shot.beat(out, stop_number=6, lead_frames=36, hold_frames=84, tail_frames=0,
              press=False)
    print(f"shot 08 -> {out}")


def shot09(scale: int) -> None:
    """A choice is made. The machine moves. 3 s: 24 waiting, the key, 48 moving."""
    out = RAW / "09_choice_taken"
    shot = TeachShot(scale)
    shot.beat(out, stop_number=8, lead_frames=0, hold_frames=24, tail_frames=48)
    print(f"shot 09 -> {out}")


def shot10(scale: int) -> None:
    """Three stops in quick succession, each a different belief and a different
    answer. 4 s: three beats of 32 frames."""
    out = RAW / "10_three_stops"
    index = 0
    for stop_number in (9, 10, 13):
        shot = TeachShot(scale)
        index = shot.beat(out, stop_number=stop_number, lead_frames=8, hold_frames=13,
                          tail_frames=11, index=index)
    print(f"shot 10 -> {out}")


def spectator(scale: int, out: Path, start_t: float, frames: int, name: str,
              logical: tuple[int, int] = (1600, 1120)) -> None:
    """The display `--tree` opens, on the induced rule, on a fixed clock.

    Taller than 16:9 on purpose: the rail lays itself out top down and drops the
    IN WORDS sentence when what is left under the tree is shorter than it needs
    (`TreePanel.move`), which at 900 px high it always is. The shot is a crop of the
    rail, so the extra height costs nothing and buys the sentence.
    """
    from phase1.__main__ import taught_rule

    out.mkdir(parents=True, exist_ok=True)
    rule = taught_rule(INDUCED)
    if rule is None:
        raise SystemExit("no induct binary: the rail cannot show the rule")
    match = MatchView(Sim(SEED, stage=True, tree=INDUCED))
    with px_scale(scale):
        from phase1.view.view import View
        view = View(match, audio=None, show=False, size=logical, rule=rule)
    view.canvas.render()
    match.advance_to(start_t)
    view.present_cold_open(T.COLD_OPEN_S)      # close the card; the match is under way
    started = time.perf_counter()
    for f in range(frames):
        match.advance_to(start_t + f * DT)
        view.draw()
        write(view.canvas.render(), out / f"{f:03d}.png")
    print(f"{name} -> {out}: {frames} frames from t={start_t:.1f}, "
          f"{(time.perf_counter() - started) / frames * 1000:.0f} ms/frame")
    view.canvas.close()


def shot12(scale: int, start_t: float, frames: int) -> None:
    """It walks on alone, nobody touching anything: the teach window between stops,
    where the footer's own words are `it is driving itself`.

    The belief-only window rather than the spectator display, which is where a taught
    rule actually drives a match: the spectator display draws the true cave beside the
    map and belongs to Act IV. This keeps the teaching act in one register.
    """
    out = RAW / "12_runs_alone"
    out.mkdir(parents=True, exist_ok=True)
    shot = TeachShot(scale)
    match = RunFactory().open(SEED, shot.spec, None)
    while True:
        match.advance_to(start_t)
        if not match.paused:
            break
        assert match.stop is not None
        match.answer(shot.chooser(match.stop))
    with px_scale(scale):
        from phase1.view.teach_view import TeachView
        view = TeachView(match, shot.registry, SESSION, show=False, size=LOGICAL)
    view.canvas.render()
    started = time.perf_counter()
    for f in range(frames):
        match.advance_to(start_t + f * DT)
        if match.paused:
            raise SystemExit(f"it stopped to ask at t={match.t:.2f}, {f} frames in")
        view.draw()
        write(view.canvas.render(), out / f"{f:03d}.png")
    print(f"shot 12 -> {out}: {frames} frames from t={start_t:.1f}, "
          f"{(time.perf_counter() - started) / frames * 1000:.0f} ms/frame")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("shot", choices=("08", "09", "10", "11", "12", "teach", "all"))
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--start", type=float, default=None)
    ap.add_argument("--frames", type=int, default=96)
    args = ap.parse_args()
    if args.shot in ("08", "teach", "all"):
        shot08(args.scale)
    if args.shot in ("09", "teach", "all"):
        shot09(args.scale)
    if args.shot in ("10", "teach", "all"):
        shot10(args.scale)
    if args.shot in ("11", "all"):
        spectator(args.scale, RAW / "11_the_rule", args.start or 296.5, args.frames, "shot 11")
    if args.shot in ("12", "all"):
        shot12(args.scale, args.start or 440.0, args.frames)


if __name__ == "__main__":
    main()
