"""Replaying a demonstration: the ghost, and the correction loop.

Nothing here builds a World. Every run is opened through a
`demo.run_source.RunSource` handed in from outside, and every comparison of two
runs' choices goes through `induct diff` -- this side does not reimplement it.
"""
