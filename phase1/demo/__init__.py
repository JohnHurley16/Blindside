"""Demonstrations: a match in which something chooses at each decision point, recorded.

**This package must never import `phase1.truth`**, and it never builds a `Sim`: it
sees a match only through the `MatchView` facade, opened for it by something outside
(`demo.run_source.RunSource`; `match.run_factory.RunFactory` is the implementation),
and a chooser sees only a `StopView`. `match/invariant.py` scans it as a downstream
package, like the renderer.
"""
