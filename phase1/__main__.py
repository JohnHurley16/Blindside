"""Run the spectator test, and teach the machine it watches.

    python -m phase1                      watch: window and sound, R sends Recall
    python -m phase1 --headless           timeline only, no window, ~2 s
    python -m phase1 --headless --recall 300
    python -m phase1 --snap 332,346,352   write spectator PNGs at those sim times
    python -m phase1 --invariant          prove nothing downstream can reach truth
    python -m phase1 --tree PATH          any tree.json drives the player (any mode)

The teaching loop (docs/CAVE-BLOCKS.md 8, 9):

    python -m phase1 --teach [--seed S] [--enabled ID,ID] [--workdir DIR]
        the window, belief only: the bot stops at each decision point, shows what it
        believes, and waits for a key; the trace is written to DIR/traces/ at the end
    python -m phase1 --teach --snap DIR   the same with no window: PNGs of the first two
                                          stops, a scripted keypress between them
    python -m phase1 --teach-scripted TREE [--seed S] [--enabled ID,ID] [--out PATH]
        the demonstration with the tree as the chooser, no window, trace written
    python -m phase1 --induce DIR         every trace in DIR/traces -> DIR/tree.json,
                                          printed as a tree and a sentence
    python -m phase1 --ghost DIR          the induced tree beside each demonstration
    python -m phase1 --correct DIR --trace N --stop K --with TREE
        scrub demonstration N to stop K, take over with TREE, promote, re-induce
    python -m phase1 --tree DIR/tree.json the match on the rule that was taught

The truth channel is off unless a display asks for it: --headless, --invariant and every
teaching mode construct a `Sim` that never builds a stage frame at all.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TYPE_CHECKING

from . import tuning as T

if TYPE_CHECKING:
    from .induct_client import InductClient
    from .policy.block_registry import BlockRegistry
    from .view.taught_rule import TaughtRule


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
                             "the card, before the match clock has started. With --teach, "
                             "a directory for the two stop pictures")
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
    parser.add_argument("--tree", type=Path, default=None,
                        help="the player's policy as a tree.json (default: the "
                             "cautious reference tree)")
    # ---- the teaching loop ----
    parser.add_argument("--teach", action="store_true",
                        help="demonstration mode: the window stops at each decision point "
                             "and waits for a key; the trace is written to --workdir")
    parser.add_argument("--teach-scripted", type=Path, default=None, metavar="TREE",
                        help="a demonstration with this tree as the chooser, no window")
    parser.add_argument("--enabled", type=str, default=None,
                        help="comma-separated block ids that exist in the demonstration")
    parser.add_argument("--workdir", type=Path, default=T.TEACH_WORKDIR,
                        help="where traces, the seam's files and the induced tree go")
    parser.add_argument("--out", type=Path, default=None,
                        help="where --teach-scripted writes its trace (default: under --workdir)")
    parser.add_argument("--induce", type=Path, default=None, metavar="DIR",
                        help="induce a tree from every trace in DIR/traces, write DIR/tree.json")
    parser.add_argument("--ghost", type=Path, default=None, metavar="DIR",
                        help="run DIR/tree.json beside each demonstration in DIR/traces")
    parser.add_argument("--correct", type=Path, default=None, metavar="DIR",
                        help="scrub demonstration --trace to stop --stop, take over with "
                             "--with, promote, re-induce")
    parser.add_argument("--trace", type=int, default=0, help="which demonstration, for --correct")
    parser.add_argument("--stop", type=int, default=0, help="which stop, for --correct")
    parser.add_argument("--with", dest="with_tree", type=Path, default=None,
                        help="the tree that takes over, for --correct")
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

    if args.teach_scripted is not None:
        raise SystemExit(run_scripted_demo(args.teach_scripted, args.seed, args.enabled,
                                           args.workdir, args.out))
    if args.induce is not None:
        raise SystemExit(run_induce(args.induce))
    if args.ghost is not None:
        raise SystemExit(run_ghost(args.ghost, args.tree))
    if args.correct is not None:
        if args.with_tree is None:
            raise SystemExit("--correct needs --with TREE")
        raise SystemExit(run_correct(args.correct, args.trace, args.stop, args.with_tree))
    if args.teach:
        raise SystemExit(run_teach(args))

    if args.headless:
        from .match.headless import run_headless
        run_headless(recall_at=args.recall, seed=args.seed, tree=args.tree)
        return

    from .match.match_view import MatchView
    from .match.sim import Sim
    from .view.backend import pick_backend

    backend = pick_backend()
    from vispy import app
    from .view.view import View

    # The one place the truth channel is switched on.
    match = MatchView(Sim(args.seed, stage=True, tree=args.tree))
    size = (args.width, args.height)
    rule = taught_rule(args.tree if args.tree is not None else T.CAUTIOUS_TREE)

    if args.record:
        from .view.recorder import Recorder
        recorder = Recorder(match, args.record, fps=args.fps, size=size,
                            with_audio=not args.no_audio, recall_at=args.recall, rule=rule)
        print(f"recording {T.COLD_OPEN_S:.0f}s of cold open, {T.MATCH_SECONDS:.0f}s of "
              f"match and the reveal at {args.fps} fps, {args.width}x{args.height}...")
        path = recorder.run()
        print(f"wrote {path}")
        return

    if args.snap:
        _snap(match, args, size, rule)
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
    view = View(match, audio=audio, show=True, size=size, rule=rule)
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


# ---- the teaching loop ------------------------------------------------------------------------
def _registry() -> "BlockRegistry":
    from .policy.block_registry import BlockRegistry
    return BlockRegistry()


def _client(workdir: Path) -> "InductClient":
    from .induct_client import InductClient
    client = InductClient(_registry().path, workdir=workdir / "seam")
    try:
        client.require()
    except FileNotFoundError as err:
        raise SystemExit(str(err)) from None
    return client


def _enabled_list(text: str | None) -> list[str] | None:
    if text is None:
        return None
    return [s.strip() for s in text.split(",") if s.strip()]


def taught_rule(tree_path: Path) -> "TaughtRule | None":
    """The tree the player watches, rendered by the seam for the spectator rail. None
    when there is no induct binary: the match runs without the rule on screen."""
    from .induct_client import InductClient
    from .view.taught_rule import TaughtRule
    client = InductClient(_registry().path)
    if not client.available():
        print(f"no induct binary at {client.binary.as_posix()}: the rail will not show the rule")
        return None
    rendered = client.render(tree_path)
    data = json.loads(tree_path.read_text(encoding="utf-8"))
    return TaughtRule(path=tree_path, lines=rendered.lines, sentence=rendered.sentence,
                      root=data["root"], params=data.get("params", {}))


def run_scripted_demo(tree_path: Path, seed: int, enabled: str | None,
                      workdir: Path, out: Path | None) -> int:
    """A demonstration in which the tree is the chooser; the trace is written."""
    from .demo.demonstration import Demonstration
    from .demo.tree_chooser import TreeChooser
    from .demo.trace_writer import TraceWriter
    from .match.run_factory import RunFactory
    from .policy.decision_tree import DecisionTree
    from .policy.run_spec import RunSpec

    registry = _registry()
    try:
        tree = DecisionTree.load(tree_path, registry)
        spec = RunSpec.for_tree(tree, registry, _enabled_list(enabled))
        chooser = TreeChooser(tree, spec)
    except ValueError as err:
        raise SystemExit(f"{tree_path.as_posix()}: {err}") from None
    match = RunFactory().open(seed, spec, None)
    trace = Demonstration(match, chooser).run()
    path = out if out is not None else workdir / "traces" / f"trace-seed-{seed}.json"
    TraceWriter.write(trace, path)
    assert trace.outcome is not None
    print(f"wrote {path.as_posix()}: seed {seed}, {len(trace.steps)} stops, "
          f"success={trace.outcome.success} lost={trace.outcome.lost} "
          f"ticks={trace.outcome.ticks} ({trace.outcome.reason}); "
          f"blocks {list(spec.enabled_predicates)} + {list(spec.enabled_actions)}")
    return 0


def _traces_in(workdir: Path) -> list[Path]:
    traces = sorted((workdir / "traces").glob("*.json"))
    if not traces:
        raise SystemExit(f"no traces under {(workdir / 'traces').as_posix()}")
    return traces


def run_induce(workdir: Path) -> int:
    """Every demonstration in the workdir in, the smallest consistent tree out --
    printed as the seam renders it -- or the two stops that contradict each other."""
    client = _client(workdir)
    traces = _traces_in(workdir)
    out = workdir / "tree.json"
    induction = client.induce(traces, out)
    print(f"induced from {len(traces)} trace(s): " + ", ".join(p.name for p in traces))
    if not induction.consistent or induction.path is None:
        print("no consistent rule fits everything that was demonstrated")
        if induction.query is not None:
            print()
            print(induction.query.text)
        return 1
    rendered = client.render(out)
    print(f"wrote {out.as_posix()}")
    print()
    print("THE INDUCED TREE")
    for line in rendered.lines:
        print(f"  {line}")
    print()
    print(f"  {rendered.sentence}")
    if induction.tree is not None and induction.tree.get("params"):
        print(f"  fitted: {induction.tree['params']}")
    # The seam's own reading of its tree against every recorded stop: the tree it
    # returned is consistent by construction, and `decide` is the authority on what
    # a tree does, so this is the number the acceptance run reads.
    agree = disagree = 0
    for path in traces:
        data = json.loads(path.read_text(encoding="utf-8"))
        for step in data["steps"]:
            chosen = client.decide(out, step["predicates"], step["raw"])
            if chosen == step["action"]:
                agree += 1
            else:
                disagree += 1
    print(f"  induct decide on every recorded stop: {agree} agree, {disagree} disagree")
    return 0


def run_ghost(workdir: Path, tree: Path | None) -> int:
    """The induced tree (or --tree) on each demonstration's seed, and where it first
    chose differently."""
    from .demo.recording import Recording
    from .demo.trace_writer import TraceWriter
    from .match.run_factory import RunFactory
    from .policy.decision_tree import DecisionTree
    from .replay.ghost import Ghost

    client = _client(workdir)
    registry = _registry()
    tree_path = tree if tree is not None else workdir / "tree.json"
    if not tree_path.is_file():
        raise SystemExit(f"no tree at {tree_path.as_posix()}; run --induce first")
    ghost = Ghost(RunFactory(), registry, client)
    loaded = DecisionTree.load(tree_path, registry)
    code = 0
    for path in _traces_in(workdir):
        recording = Recording(trace=TraceWriter.read(path), path=path)
        if not ghost.can_run(recording, loaded):
            print(f"{path.name}: the tree names blocks this run never had; skipped")
            continue
        result = ghost.run(recording, tree_path)
        print(f"{path.name} (seed {result.seed}): {result.summary()}")
        if result.first_difference is not None:
            code = 1
    return code


def run_correct(workdir: Path, which: int, stop: int, with_tree: Path) -> int:
    """Scrub demonstration `which` to stop `stop`, let `with_tree` take over from
    there, promote the suffix in place of the old one, and induce again. The scripted
    form of the correction loop; the window's form is `--teach --resume`."""
    import time

    from .demo.recording import Recording
    from .demo.tree_chooser import TreeChooser
    from .demo.trace_writer import TraceWriter
    from .match.run_factory import RunFactory
    from .policy.decision_tree import DecisionTree
    from .policy.run_spec import RunSpec
    from .replay import correction

    client = _client(workdir)
    registry = _registry()
    paths = _traces_in(workdir)
    if not 0 <= which < len(paths):
        raise SystemExit(f"--trace {which}: there are {len(paths)} demonstrations")
    recordings = [Recording(trace=TraceWriter.read(p), path=p) for p in paths]
    original = recordings[which]
    trace = original.trace
    tree = DecisionTree.load(with_tree, registry)
    chooser = TreeChooser(tree, RunSpec.from_trace(trace.enabled_predicates,
                                                   trace.enabled_actions, trace.params))
    started = time.perf_counter()
    takeover = correction.scrub(RunFactory(), original, stop)
    print(f"scrubbed {original.path.name} to stop {stop} (tick {trace.steps[stop].tick}, "
          f"place {trace.steps[stop].junction}); {with_tree.name} takes over")
    while not takeover.done:
        assert takeover.stop is not None
        takeover.choose(chooser(takeover.stop))
    suffix = takeover.suffix()
    changed = [s.action for s in trace.steps[stop:]] != [s.action for s in suffix]
    promoted = correction.promote(trace, stop, suffix, TraceWriter.from_match(takeover.match).outcome)
    backup = original.path.with_suffix(".before-correction.json")
    TraceWriter.write(trace, backup)
    recordings[which] = Recording(trace=promoted, path=original.path)
    out = workdir / "tree.json"
    induction, _ = correction.reinduce(client, recordings, out)
    seconds = time.perf_counter() - started
    print(f"promoted stop {stop} onward ({'the suffix changed' if changed else 'the suffix came back identical'}: "
          f"{len(trace.steps) - stop} old steps -> {len(suffix)} new); the old trace is at {backup.name}")
    print(f"re-induced: {'consistent' if induction.consistent else 'INCONSISTENT'}; "
          f"scrub -> take over -> promote -> re-induce in {seconds:.2f} s wall clock")
    if induction.consistent and induction.path is not None:
        rendered = client.render(out)
        for line in rendered.lines:
            print(f"  {line}")
        print(f"  {rendered.sentence}")
        return 0
    if induction.query is not None:
        print(induction.query.text)
    return 1


def run_teach(args: argparse.Namespace) -> int:
    """The window, belief only, stopping at every decision point for a key."""
    from .match.run_factory import RunFactory
    from .policy.run_spec import RunSpec
    from .view.backend import pick_backend

    registry = _registry()
    try:
        spec = RunSpec.for_demonstration(registry, _enabled_list(args.enabled))
    except ValueError as err:
        raise SystemExit(str(err)) from None
    match = RunFactory().open(args.seed, spec, None)
    workdir: Path = args.workdir
    backend = pick_backend()
    from vispy import app
    from .view.teach_view import TeachView

    size = (args.width, args.height)
    if args.snap:
        return _teach_snap(match, registry, Path(args.snap), size)

    print("preparing the display...", flush=True)
    view = TeachView(match, registry, workdir, show=True, size=size)
    view.canvas.show()
    view.draw()
    view.canvas.render()
    view.draw()
    view.canvas.render()
    view.reset_clock()
    keys = "   ".join(f"{i + 1} {registry.action(a).label}"
                      for i, a in enumerate(spec.enabled_actions))
    print(f"ready.  backend {backend}.  When it stops:  {keys}   Q quit", flush=True)
    frame_clock = app.Timer(interval=1 / 60, connect=lambda ev: view.advance(),
                            start=True, app=view.canvas.app)
    app.run()
    del frame_clock
    path = view.finish()
    if path is not None:
        print(f"wrote {path.as_posix()}")
    return 0


def _teach_snap(match: object, registry: "BlockRegistry", out: Path,
                size: tuple[int, int]) -> int:
    """The teach window with no screen: run to the first stop, take a picture, press
    a key the way the window would, run to the next stop, take another."""
    from .view.teach_view import TeachView

    out.mkdir(parents=True, exist_ok=True)
    view = TeachView(match, registry, out, show=False, size=size)   # type: ignore[arg-type]
    written: list[Path] = []
    for index in range(2):
        view.advance()                     # the live frame path, once, for its clock
        stop = view.run_to_stop()
        if stop is None:
            print("the match ended before a second stop")
            break
        path = out / f"teach_stop{index + 1}.png"
        view.snapshot(str(path))
        written.append(path)
        offered = [a for a in match.spec.enabled_actions if stop.available.get(a, True)]   # type: ignore[attr-defined]
        print(f"stop {index + 1} at {int(stop.t) // 60}:{stop.t % 60:04.1f} (tick {stop.tick}, "
              f"place {stop.junction}, {stop.reason}): "
              + ", ".join(f"{pid}={'yes' if v else 'no'}"
                          + (f" ({stop.raw[pid]:.3g})" if pid in stop.raw else "")
                          for pid, v in stop.predicates.items())
              + f"; offered {offered}")
        print(f"wrote {path.as_posix()}")
        # A scripted keypress: the first offered action's number key, through the
        # same handler the window binds.
        key = str(match.spec.enabled_actions.index(offered[0]) + 1)   # type: ignore[attr-defined]
        view.press(key)
        print(f"pressed {key} -> {registry.action(offered[0]).label}; "
              f"paused={match.paused}")   # type: ignore[attr-defined]
    return 0


def _snap(match: object, args: argparse.Namespace, size: tuple[int, int],
          rule: "TaughtRule | None") -> None:
    """Render the screen at a list of sim times, with no window.

    Snapshots are how this gets iterated, and the times that matter for slice 1 are
    332, 346 and 352 -- the thirty-five seconds either side of the near miss.
    """
    from pathlib import Path

    from .view.view import View

    out = Path(args.snap_dir)
    out.mkdir(parents=True, exist_ok=True)
    view = View(match, audio=None, show=False, size=size, rule=rule)   # type: ignore[arg-type]
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
