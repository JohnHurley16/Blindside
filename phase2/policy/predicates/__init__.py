"""Predicate evaluators, one per file.

Each module exposes `evaluate(belief, params) -> (bool, raw | None)`. None of them
knows its own id; the block registry is the one place ids meet evaluators.
"""
