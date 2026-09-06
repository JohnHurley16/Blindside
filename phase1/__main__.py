"""Run the spectator test.

    python -m phase1                      play: window and sound, R sends Recall
    python -m phase1 --headless           timeline only, no window, ~2 s
    python -m phase1 --headless --recall 300
    python -m phase1 --snap 60,200,400    write belief-view PNGs at those times
    python -m phase1 --invariant          prove belief and policy cannot reach truth
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
                        help="comma-separated sim times; render PNGs with no window")
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--player-sensor", choices=("lidar", "sonar"), default=None,
                        help="the player's active sensor (default: tuning.PLAYER_SENSOR)")
    parser.add_argument("--rival-sensor", choices=("lidar", "sonar"), default=None)
    parser.add_argument("--record", type=str, default=None,
                        help="render the whole match to this .mp4, with sound, and exit")
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--width", type=int, default=1400)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--invariant", action="store_true",
                        help="check the truth/belief boundary and exit")
    args = parser.parse_args()

    if args.player_sensor:
        T.PLAYER_SENSOR = args.player_sensor      # type: ignore[misc]
    if args.rival_sensor:
        T.RIVAL_SENSOR = args.rival_sensor        # type: ignore[misc]

    if args.invariant:
        from .match.invariant import assert_clean
        assert_clean()
        print("invariant holds: belief and policy cannot reach truth")
        return

    if args.headless:
        from .match.headless import run_headless
        run_headless(recall_at=args.recall, seed=args.seed)
        return

    from .match.sim import Sim
    from .view.backend import pick_backend

    backend = pick_backend()
    from vispy import app
    from .view.view import View

    sim = Sim(args.seed)

    if args.record:
        from .view.recorder import Recorder
        recorder = Recorder(sim, args.record, fps=args.fps,
                            size=(args.width, args.height),
                            with_audio=not args.no_audio,
                            recall_at=args.recall)
        print(f"recording {T.MATCH_SECONDS:.0f}s of match plus the reveal "
              f"at {args.fps} fps, {args.width}x{args.height}...")
        path = recorder.run()
        print(f"wrote {path}")
        return

    if args.snap:
        view = View(sim, audio=None, show=False)
        for at in sorted(float(x) for x in args.snap.split(",")):
            while sim.t < at and not sim.over:
                if args.recall is not None and sim.t >= args.recall and not sim.recall_used:
                    sim.recall()
                sim.step()
                if sim.tick % 10 == 0:
                    sim.record_truth_trail()
            path = f"snap_{int(at):03d}.png"
            view.snapshot(path)
            print(f"wrote {path}  sim t={sim.t:.1f}{'  (over)' if sim.over else ''}")
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
    # look at.
    print("preparing the display (about ten seconds)...", flush=True)
    view = View(sim, audio=audio, show=True)
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

    # The frame clock. Owned here, bound to the canvas's own Application, and held in
    # a local for the lifetime of the event loop -- every other arrangement produced a
    # timer that fired once or never, and a window that never drew a second frame.
    frame_clock = app.Timer(interval=1 / 60, connect=lambda ev: view.advance(),
                            start=True, app=view.canvas.app)

    auto_clock = None
    if args.recall is not None:
        def auto_recall(ev: object) -> None:
            if sim.t >= args.recall and not sim.recall_used:
                sim.recall()
        auto_clock = app.Timer(interval=0.5, connect=auto_recall, start=True,
                               app=view.canvas.app)

    print(f"backend {backend}; audio {'on' if audio is not None and audio.ok else 'silent'}. "
          f"R = Recall, left drag orbits, wheel zooms.")
    app.run()
    if audio is not None:
        audio.close()


if __name__ == "__main__":
    main()
