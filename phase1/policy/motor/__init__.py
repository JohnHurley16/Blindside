"""The motor layer: what an action does between decision points.

The tree answers *what am I trying to do*; the motor answers *how do I do it from
here* (CAVE-BLOCKS.md 4). Everything here is the engine the hand-written policy
already had -- steering, wall escape, jam breaking, the search spiral, the load dwell,
the interface creep -- cut along the line between a decision and the carrying-out of
one. One program per action, one class per file, and a `Driver` they share the
shape of. None of it names a block; the registry does that.

Reads Belief only. **This package must never import `phase1.truth`.**
"""
