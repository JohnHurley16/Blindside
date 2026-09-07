"""Ground truth. Never visible to a policy.

Only `phase2.sensing.sensor_rig`, `phase2.match` and `phase2.eval` may import this
package. `python -m phase2 --invariant` checks that belief, policy, motor and demo
do not.
"""
