"""Run the spectator test.

    python -m phase1                      watch: window and sound, R sends Recall
    python -m phase1 --headless           timeline only, no window, ~2 s
    python -m phase1 --headless --recall 300
    python -m phase1 --snap 332,346,352   write spectator PNGs at those sim times
    python -m phase1 --invariant          prove nothing downstream can reach truth

The truth channel is off unless a display asks for it: --headless and --invariant
construct a `Sim` that never builds a stage frame at all.
"""
from __future__ import annotations

import argparse

from . import tuning as T


def main() -> None:
    parser = argparse.ArgumentParser(prog="phase1")
    parser.add_argument("--seed", type=int, default=T.SEED)
    parser.add_argument("--recall", type=float, default=None,
                        help="send the single Recall command at this many seconds")
    parser.add_argument("--headless", action="store_true",
                        help="run the match with no window and print the timeline")
    parser.add_argument("--snap", type=str, default=None,
                        help="comma-separated sim times; render PNGs with no window. "
                             "A NEGATIVE time is cold-open time, which the beat sheet "
                             "writes as -0:06 to 0:00: --snap=-3 is three seconds into "
                             "the card, before the match clock has started")
    parser.add_argument("--snap-dir", type=str, default=".",
                        help="where --snap writes its PNGs")
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--player-sensor", choices=("lidar", "sonar"), default=None,
                        help="the player's active sensor (default: tuning.PLAYER_SENSOR)")
    parser.add_argument("--rival-sensor", choices=("lidar", "sonar"), default=None)
    parser.add_argument("--record", type=str, default=None,
                        help="render the whole match to this .mp4, with sound, and exit")
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--width", type=int, default=T.CANVAS_W)
    parser.add_argument("--height", type=int, default=T.CANVAS_H)
    parser.add_argument("--frame-times", type=int, default=0,
                        help="paint this many live frames, print the timings, and exit")
    parser.add_argument("--invariant", action="store_true",
                        help="check the truth/belief boundary and exit")
    args = parser.parse_args()

    if args.player_sensor:
        T.PLAYER_SENSOR = args.player_sensor      # type: ignore[misc]
    if args.rival_sensor:
        T.RIVAL_SENSOR = args.rival_sensor        # type: ignore[misc]

    if args.invariant:
        from .match.invariant import assert_clean, summary
        assert_clean()
        print(summary())
        return

    if args.headless:
        from .match.headless import run_headless
        run_headless(recall_at=args.recall, seed=args.seed)
        return

    from .match.match_view import MatchView
    from .match.sim import Sim
    from .view.backend import pick_backend

    backend = pick_backend()
    from vispy import app
    from .view.view import View

    # The one place the truth channel is switched on.
    match = MatchView(Sim(args.seed, stage=True))
    size = (args.width, args.height)

    if args.record:
        from .view.recorder import Recorder
        recorder = Recorder(match, args.record, fps=args.fps, size=size,
                            with_audio=not args.no_audio, recall_at=args.recall)
        print(f"recording {T.COLD_OPEN_S:.0f}s of cold open, {T.MATCH_SECONDS:.0f}s of "
              f"match and the reveal at {args.fps} fps, {args.width}x{args.height}...")
        path = recorder.run()
        print(f"wrote {path}")
        return

    if args.snap:
        _snap(match, args, size)
        return

    audio = None
    if not args.no_audio:
        from .audio.mixer import Mixer
        audio = Mixer()
    # Build the window hidden and take the first two paints offscreen. The first
    # compiles a shader for every visual and the second builds a glyph atlas for
    # every string, and together they froze the event loop for eleven seconds --
    # which, on a window that had already appeared, looked like a black screen
    # that never did anything. Done here, they finish before there is anything to
    # look at. The cave mesh adds one 43,202-triangle upload to that warm-up.
    print("preparing the display (about ten seconds)...", flush=True)
    view = View(match, audio=audio, show=True, size=size)
    # The window must be on screen before an offscreen render: render() on a canvas
    # that has never been shown leaves vispy's framebuffer stack empty, and every
    # on-screen paint after that dies with an IndexError inside glBindFramebuffer.
    view.canvas.show()
    view.advance()
    view.canvas.render()
    view.advance()
    view.canvas.render()
    view._wall_clock_zero = None       # the match clock starts now, not during warm-up
    print("ready.", flush=True)

    if args.frame_times:
        _frame_times(view, args.frame_times)
        return

    # The frame clock. Owned here, bound to the canvas's own Application, and held in
    # a local for the lifetime of the event loop -- every other arrangement produced a
    # timer that fired once or never, and a window that never drew a second frame.
    frame_clock = app.Timer(interval=1 / 60, connect=lambda ev: view.advance(),
                            start=True, app=view.canvas.app)

    auto_clock = None
    if args.recall is not None:
        def auto_recall(ev: object) -> None:
            if match.t >= args.recall and not match.recall_used:
                match.recall()
        auto_clock = app.Timer(interval=0.5, connect=auto_recall, start=True,
                               app=view.canvas.app)

    print(f"backend {backend}; audio {'on' if audio is not None and audio.ok else 'silent'}. "
          f"R = Recall. The camera is the director's.")
    app.run()
    if audio is not None:
        audio.close()


def _snap(match: object, args: argparse.Namespace, size: tuple[int, int]) -> None:
    """Render the screen at a list of sim times, with no window.

    Snapshots are how this gets iterated, and the times that matter for slice 1 are
    332, 346 and 352 -- the thirty-five seconds either side of the near miss.
    """
    from pathlib import Path

    from .view.view import View

    out = Path(args.snap_dir)
    out.mkdir(parents=True, exist_ok=True)
    view = View(match, audio=None, show=False, size=size)   # type: ignore[arg-type]
    # Match times ascending -- `advance_to` only moves forward -- and the cold open after
    # all of them, because driving the card mutes every other string on the screen and it
    # stays muted until the six seconds are up, which is never inside a snapshot.
    times = sorted((float(x) for x in args.snap.split(",")), key=lambda x: (x < 0.0, x))
    for at in times:
        if at < 0.0:
            # Cold-open time, which section 5's beat sheet writes as -0:06 to 0:00. The
            # card runs before the match clock, so it has no sim time to be asked for.
            view.present_cold_open(-at)
            path = out / f"snap_open_{int(-at):03d}.png"
            view.snapshot(str(path))
            print(f"wrote {path}  cold open at -0:{int(-at):02d}")
            continue
        if args.recall is not None and at >= args.recall:
            if not match.recall_used:                        # type: ignore[attr-defined]
                match.recall()                               # type: ignore[attr-defined]
        match.advance_to(at)                                 # type: ignore[attr-defined]
        path = out / f"snap_{int(at):03d}.png"
        view.snapshot(str(path))
        print(f"wrote {path}  sim t={match.t:.1f}"            # type: ignore[attr-defined]
              f"{'  (over)' if match.over else ''}")          # type: ignore[attr-defined]


def _frame_times(view: object, frames: int) -> None:
    """Paint N live frames and report the distribution, the way phase 1 measured it
    before: canvas.update() plus process_events() on a shown canvas, so the number is
    a whole frame -- sim, draw and paint -- and not just the draw."""
    import statistics
    import time

    from vispy import app

    samples: list[float] = []
    for _ in range(frames):
        start = time.perf_counter()
        view.advance()                                       # type: ignore[attr-defined]
        app.process_events()
        samples.append((time.perf_counter() - start) * 1000.0)
    samples.sort()
    print(f"live frame time over {frames} frames, ms: "
          f"median {statistics.median(samples):.1f}  "
          f"mean {statistics.fmean(samples):.1f}  "
          f"p90 {samples[int(0.9 * (frames - 1))]:.1f}  "
          f"worst {samples[-1]:.1f}  best {samples[0]:.1f}")


if __name__ == "__main__":
    main()
