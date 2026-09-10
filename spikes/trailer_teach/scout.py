"""List every stop of a scripted teaching session, so shots can be chosen off it.

Read-only on phase1: builds the same objects `--teach-scripted` builds and runs the
same demonstration loop, printing what the window would show at each stop.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from phase1.demo.tree_chooser import TreeChooser          # noqa: E402
from phase1.match.run_factory import RunFactory           # noqa: E402
from phase1.policy.block_registry import BlockRegistry    # noqa: E402
from phase1.policy.decision_tree import DecisionTree      # noqa: E402
from phase1.policy.run_spec import RunSpec                # noqa: E402

ALL = None   # every block


def main(seed: int, tree_path: Path) -> None:
    registry = BlockRegistry()
    spec = RunSpec.for_demonstration(registry, ALL)
    tree = DecisionTree.load(tree_path, registry)
    # the demonstration spec's provisional thresholds, but the tree's own where it has them
    params = dict(spec.params)
    for pid, vals in tree.params.items():
        if pid in params:
            params[pid] = dict(vals)
    spec = RunSpec(spec.enabled_predicates, spec.enabled_actions, params)
    chooser = TreeChooser(tree, spec)
    match = RunFactory().open(seed, spec, None)
    n = 0
    prev_t = 0.0
    while (stop := match.advance_to_stop()) is not None:
        n += 1
        offered = [a for a in spec.enabled_actions if stop.available.get(a, True)]
        chosen = chooser(stop)
        key = spec.enabled_actions.index(chosen) + 1
        preds = " ".join(
            f"{pid}={'Y' if v else 'n'}" + (f"({stop.raw[pid]:.3g})" if pid in stop.raw else "")
            for pid, v in stop.predicates.items())
        print(f"stop {n:2d}  t={stop.t:7.2f}  (+{stop.t - prev_t:6.2f})  tick={stop.tick:5d}  "
              f"why={stop.reason:26s} key={key} -> {registry.action(chosen).label}")
        print(f"          {preds}")
        print(f"          offered: {[registry.action(a).label for a in offered]}")
        prev_t = stop.t
        match.answer(chosen)
    print(f"\n{n} stops; match over at t={match.t:.1f}; "
          f"{match.result.player_outcome if match.result else '?'}")


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    tree = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "phase1" / "reference" / "cautious.json"
    main(seed, tree)
