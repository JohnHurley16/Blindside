"""Phase 2 -- the Junction Test. Throwaway Python.

The one invariant holds here as everywhere: a policy reads Belief, never World.
`phase2.sensing.sensor_rig` is the only module that reads both, and
`python -m phase2 --invariant` checks that belief, policy, motor and demo cannot
reach `phase2.truth`.
"""
