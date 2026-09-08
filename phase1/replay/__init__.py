"""Replaying a demonstration: the ghost, and the correction loop.

Nothing here builds a Sim. Every match is opened through a `demo.run_source.RunSource`
handed in from outside, and every comparison of two runs' choices goes through
`induct diff` -- this side does not reimplement it. `match/invariant.py` scans this
package as a downstream one, like the renderer.
"""
