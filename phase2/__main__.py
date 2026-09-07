"""Run the junction test's Python side.

    python -m phase2                       the window: the staged tutorial, then induce
    python -m phase2 --scripted            the whole session with no window, at sim speed
    python -m phase2 --snap PATH           the scripted session offscreen, two PNGs from PATH
    python -m phase2 --invariant
    python -m phase2 --headless --tree TREE.json --seeds N [--seed-start S]
    python -m phase2 --demo-scripted --tree TREE.json --seed S --out TRACE.json [--enabled ID,ID]

`--snap` takes a stem rather than a file: it writes `<stem>-run3-stop.png` (a stop in
the third staged run, the first full one) and `<stem>-tree.png` (the panel after the
induction), because the two moments worth a picture are not the same moment.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .view.session_controller import SessionController
    from .view.view import View

REFERENCE_DIR: Path = Path(__file__).resolve().parent / "reference"
THETA_AWARE: Path = REFERENCE_DIR / "theta_aware.json"


def run_scripted_demo(tree_path: Path, seed: int, out: Path, enabled: str | None) -> None:
    """A demonstration in which the tree is the chooser; the trace is written."""
    from .demo.demonstration import Demonstration
    from .demo.stop_view import StopView
    from .demo.trace_writer import TraceWriter
    from .match.driver_view import DriverView
    from .match.session import Session
    from .policy.block_registry import BlockRegistry
    from .policy.decision_tree import DecisionTree
    from .policy.policy import Policy
    from .truth.world import World

    registry = BlockRegistry()
    enabled_predicates = registry.predicate_ids()
    enabled_actions = registry.action_ids()
    if enabled is not None:
        wanted = {s.strip() for s in enabled.split(",") if s.strip()}
        unknown = wanted - set(enabled_predicates) - set(enabled_actions)
        if unknown:
            raise SystemExit(f"--enabled names blocks not in the block list: {sorted(unknown)}")
        enabled_predicates = [p for p in enabled_predicates if p in wanted]
        enabled_actions = [a for a in enabled_actions if a in wanted]
    try:
        tree = DecisionTree.load(tree_path, registry)
        policy = Policy(tree, enabled_predicates, enabled_actions)
    except ValueError as err:
        raise SystemExit(f"{tree_path.as_posix()}: {err}") from None
    try:
        session = Session(World(seed), registry, enabled_predicates=enabled_predicates,
                          enabled_actions=enabled_actions, params=policy.params)
    except ValueError as err:
        raise SystemExit(f"{err}; pass --enabled without that block, or a tree that sets it") from None

    def chooser(view: StopView) -> str:
        return policy.choose(view.belief)

    # The demonstration is handed the narrow face of the session, never the
    # session: a Session has `world` on it, and a demonstration keeps its driver
    # for the whole run. See match/invariant.py, part 3.
    trace = Demonstration(DriverView(session), chooser).run()
    path = TraceWriter.write(trace, out)
    assert trace.outcome is not None
    print(f"wrote {path.as_posix()}: seed {seed}, {len(trace.steps)} stops, "
          f"success={trace.outcome.success} lost={trace.outcome.lost} ticks={trace.outcome.ticks}")


# ---- the session ----------------------------------------------------------------------------
def build_session(workdir: Path, scripted: bool) -> tuple["SessionController",
                                                          object, object]:
    """The controller, the factory that opens its runs, and the block registry.

    The factory is the only object here that has a World in it, and it is handed to
    the controller as a `RunSource`; that is the whole of why `view` and `replay`
    pass the invariant check.
    """
    from .demo.stage import Stage
    from .demo.stop_view import StopView
    from .demo.tutorial import Tutorial
    from .induct_client import InductClient
    from .match.run_factory import RunFactory
    from .policy.block_registry import BlockRegistry
    from .policy.decision_tree import DecisionTree
    from .policy.policy import Policy
    from .view.session_controller import Chooser, SessionController

    registry = BlockRegistry()
    tutorial = Tutorial(registry)
    factory = RunFactory(registry)
    client = InductClient(registry.path, workdir=workdir / "seam")
    try:
        client.require()          # fail here, not four runs in
    except FileNotFoundError as err:
        raise SystemExit(str(err)) from None

    chooser_for = None
    if scripted:
        cache: dict[int, Chooser] = {}

        def chooser_for_stage(stage: Stage) -> Chooser:
            """The reference policy, restricted to the blocks the run has.

            A run with one action has no decision to make, so the chooser is that
            action; this is what lets the tutorial's first run be scripted without
            anything here naming a block.
            """
            if stage.block_stage in cache:
                return cache[stage.block_stage]
            actions = tutorial.actions(stage)
            if len(actions) == 1:
                only = actions[0]

                def single(view: StopView) -> str:
                    return only
                cache[stage.block_stage] = single
                return single
            policy = Policy(DecisionTree.load(THETA_AWARE, registry),
                            tutorial.predicates(stage), actions)

            def by_tree(view: StopView) -> str:
                return policy.choose(view.belief)
            cache[stage.block_stage] = by_tree
            return by_tree

        chooser_for = chooser_for_stage

    controller = SessionController(factory, registry, tutorial, client,
                                   workdir / "traces", chooser_for=chooser_for)
    return controller, factory, registry


def report(controller: "SessionController") -> int:
    """Print what the session produced. The exit code the acceptance run reads."""
    from .view.phase import Phase
    print()
    for line in controller.log:
        print(f"  {line}")
    induction = controller.reinduction or controller.induction
    rendered = controller.rendered
    print()
    if induction is None or not induction.consistent or rendered is None:
        print("no consistent rule was induced")
        if induction is not None and induction.query is not None:
            print(induction.query.text)
        return 1
    print("THE INDUCED TREE")
    for line in rendered.lines:
        print(f"  {line}")
    print(f"\n  {rendered.sentence}")
    if induction.tree is not None and induction.tree.get("params"):
        print(f"  fitted: {induction.tree['params']}")
    ghost = controller.ghost
    if ghost is not None:
        print(f"\nGHOST  seed {ghost.seed}: {ghost.summary()}")
    if controller.seam_check:
        print(f"       {controller.seam_check}")
    seconds = controller.correction_seconds
    second = controller.reinduction
    if seconds is not None and second is not None:
        print(f"CORRECTION  scrub -> take over -> promote -> re-induce: {seconds:.2f} s "
              f"wall clock, re-induced "
              f"{'consistent' if second.consistent else 'INCONSISTENT'}")
    return 0 if controller.phase is Phase.DONE else 1


def run_headless_session(workdir: Path) -> int:
    started = time.perf_counter()
    controller, _, _ = build_session(workdir, scripted=True)
    while controller.pump():
        pass
    code = report(controller)
    print(f"\nwhole session: {time.perf_counter() - started:.1f} s")
    return code


def run_snap(workdir: Path, stem: Path) -> int:
    """The scripted session with a hidden window, stopping twice for a picture."""
    from .view.backend import pick_backend
    pick_backend()
    from .view.phase import Phase
    from .view.view import View

    controller, factory, registry = build_session(workdir, scripted=True)
    view = View(controller, registry, reveal=factory.reveal, show=False)
    written: list[Path] = []
    run3 = stem.with_name(stem.name + "-run3-stop.png")
    tree = stem.with_name(stem.name + "-tree.png")
    stops_in_run3 = 0
    shot_run3 = shot_tree = False
    while controller.pump():
        if not shot_run3 and controller.stage.number == 3 \
                and controller.phase is Phase.STOP:
            stops_in_run3 += 1
            if stops_in_run3 == 6:
                shot_run3 = True
                written.append(view.snapshot(run3))
        if not shot_tree and controller.phase is Phase.PROMOTED:
            shot_tree = True
            written.append(view.snapshot(tree))
    code = report(controller)
    for path in written:
        print(f"wrote {path.as_posix()}")
    return code


def run_window(workdir: Path) -> int:
    from vispy import app

    from .view.backend import pick_backend
    print(f"vispy backend: {pick_backend()}")
    from .view.view import View

    controller, factory, registry = build_session(workdir, scripted=False)
    print("preparing the display...", flush=True)
    view = View(controller, registry, reveal=factory.reveal)
    view.canvas.show()
    view.draw()
    view.canvas.render()
    view.draw()
    print("ready.  1/2 choose   SPACE next   G ghost   arrows scrub   T take over   "
          "P promote   Q quit", flush=True)

    # The frame clock, owned here and bound to the canvas's own Application, held in
    # a local for the lifetime of the event loop: Phase 1's timer created inside the
    # view fired once and then never again. Nothing animates between stops, so ten
    # hertz is enough to keep the panels honest.
    clock = app.Timer(interval=0.1, connect=lambda ev: _frame(view), start=True,
                      app=view.canvas.app)
    app.run()
    del clock
    return report(controller)


def _frame(view: "View") -> None:
    view.draw()
    view.canvas.update()


def main() -> None:
    parser = argparse.ArgumentParser(prog="phase2")
    parser.add_argument("--invariant", action="store_true",
                        help="check the truth/belief boundary and exit")
    parser.add_argument("--headless", action="store_true",
                        help="run a tree on N seeds with no window and print the table")
    parser.add_argument("--demo-scripted", action="store_true",
                        help="run a demonstration with the tree as chooser and write the trace")
    parser.add_argument("--scripted", action="store_true",
                        help="drive the whole staged session with the reference tree, no window")
    parser.add_argument("--snap", type=Path, default=None,
                        help="the scripted session offscreen; PNG stem for the two pictures")
    parser.add_argument("--workdir", type=Path, default=Path("phase2-session"),
                        help="where traces and induced trees are written")
    parser.add_argument("--tree", type=Path, default=None)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--enabled", type=str, default=None,
                        help="comma-separated block ids that exist in the scripted demo")
    args = parser.parse_args()

    if args.invariant:
        from .match.invariant import assert_clean
        assert_clean()
        print("invariant holds: belief, policy, motor, demo, replay and view "
              "cannot reach truth")
        return

    if args.headless:
        if args.tree is None:
            raise SystemExit("--headless needs --tree")
        from .eval.evaluator import Evaluator
        from .policy.block_registry import BlockRegistry
        Evaluator(args.tree, BlockRegistry()).run(range(args.seed_start, args.seed_start + args.seeds))
        return

    if args.demo_scripted:
        if args.tree is None or args.out is None:
            raise SystemExit("--demo-scripted needs --tree and --out")
        run_scripted_demo(args.tree, args.seed, args.out, args.enabled)
        return

    if args.snap is not None:
        raise SystemExit(run_snap(args.workdir, args.snap))

    if args.scripted:
        raise SystemExit(run_headless_session(args.workdir))

    raise SystemExit(run_window(args.workdir))


if __name__ == "__main__":
    main()
