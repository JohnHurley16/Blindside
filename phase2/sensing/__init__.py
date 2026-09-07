"""The sensor layer: the only place where truth becomes belief.

`sensor_rig.SensorRig` is the single class permitted to read `phase2.truth`. This
package's `__init__` deliberately imports nothing, so that importing the returns
from belief does not drag the rig -- and truth -- along with it.
"""
