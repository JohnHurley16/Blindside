"""Entry point.

    python -m phase1              headless timeline, no recall
    python -m phase1 --recall 300 headless timeline, recall sent at 5:00
    python -m phase1 --invariant  check that belief and policy cannot reach truth
"""
from __future__ import annotations

import argparse

from .match.headless import run_headless
from .match.invariant import assert_clean


def main() -> None:
    parser = argparse.ArgumentParser(prog="phase1")
    parser.add_argument("--recall", type=float, default=None,
                        help="send the single Recall command at this time, in seconds")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--invariant", action="store_true",
                        help="check the truth/belief boundary and exit")
    args = parser.parse_args()

    if args.invariant:
        assert_clean()
        print("invariant holds: belief and policy cannot reach truth")
        return

    from . import tuning as T
    run_headless(recall_at=args.recall, seed=args.seed if args.seed is not None else T.SEED)


if __name__ == "__main__":
    main()
