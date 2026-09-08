"""What damage now costs. THE-MACHINERY 11's replacement effects, measured.

The odometry A/B failed because position error is a whole-path quantity and the two
paths diverge for reasons that have nothing to do with the effect. Ground covered per
second of walking, and the reach of a sweep, are DIRECT -- they are the effect itself
rather than a downstream consequence of it -- so a divergent path cannot launder them.

Both runs are measured from the same instant: the tick at which the SHIPPED run's
damage first crosses the drive rung, so nothing before the break is averaged in.
"""
import sys

sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")

import numpy as np

from phase1 import tuning as T
from phase1.match.sim import Sim
from phase1.point_source import PointSource
from phase1.sensing.returns import RangeBearingReturn
from phase1.sensing.sensor_rig import SensorRig

ACTIVE = (PointSource.SONAR, PointSource.LIDAR)


def run(seed, effects_on, watch, since):
    if effects_on:
        T.DAMAGE_RANGE_FROM, T.DAMAGE_SPEED_FROM = 0.20, 0.30      # type: ignore[misc]
    else:
        T.DAMAGE_RANGE_FROM, T.DAMAGE_SPEED_FROM = 9.9, 9.9        # type: ignore[misc]

    sim = Sim(seed)
    reach = []
    real = SensorRig.sample

    def spy(self, world, me, cmd, t):
        out = real(self, world, me, cmd, t)
        if self.name != watch or t < since:
            return out
        rs = [r.range for r in out
              if isinstance(r, RangeBearingReturn) and r.source in ACTIVE]
        if rs:
            reach.append(max(rs))
        return out

    SensorRig.sample = spy                                          # type: ignore[assignment]
    try:
        walked = moved_s = 0.0
        crossed = None
        while not sim.over:
            sim.step()
            ag = sim._world.agents[watch]
            if crossed is None and ag.damage >= 0.30:
                crossed = sim.t
            if sim.t >= since:
                d = ag.last_true_delta[0]
                walked += d
                if d > 1e-9:
                    moved_s += T.DT
    finally:
        SensorRig.sample = real                                     # type: ignore[assignment]
    return dict(walked=walked, moved_s=moved_s, reach=np.array(reach or [0.0]),
                crossed=crossed, damage=sim._world.agents[watch].damage,
                over_at=sim.t)


def ab(seed, watch):
    probe = run(seed, True, watch, 1e9)
    since = probe["crossed"]
    print(f"\n=== seed {seed}, the {watch}: damage {probe['damage']:.3f}, "
          f"crosses the drive rung at {since if since else float('nan'):.1f} s "
          f"({probe['over_at'] - (since or 0):.0f} s of match left) ===")
    if since is None:
        print("  never crosses; nothing to measure")
        return
    rows = []
    for tag, on in (("OFF     ", False), ("SHIPPED ", True)):
        r = run(seed, on, watch, since)
        speed = r["walked"] / max(r["moved_s"], 1e-9)
        rows.append((tag, r, speed))
        print(f"  {tag} walked {r['walked']:7.2f} cells in {r['moved_s']:6.1f} s of "
              f"motion -> {speed:6.4f} cells/s;   sweeps n={len(r['reach']):3d}  "
              f"furthest return mean {r['reach'].mean():6.2f}  "
              f"p90 {np.percentile(r['reach'], 90):6.2f}  max {r['reach'].max():6.2f}")
    (_, a, sa), (_, b, sb) = rows
    print(f"  DELTA    speed {100 * (sb / sa - 1):+.1f}%   "
          f"ground covered {100 * (b['walked'] / max(a['walked'], 1e-9) - 1):+.1f}%   "
          f"mean reach {100 * (b['reach'].mean() / max(a['reach'].mean(), 1e-9) - 1):+.1f}%   "
          f"max reach {100 * (b['reach'].max() / max(a['reach'].max(), 1e-9) - 1):+.1f}%")


ab(7, "player")
ab(1, "rival")

# ---- the bench: same pose, damage the only variable ---------------------------------------
print("\n=== bench: the two curves, with nothing else moving ===")
from phase1.truth.agent_truth import AgentTruth

print(f"  {'damage':>7} {'speed x':>9} {'range x':>9} {'sonar reach':>12} "
      f"{'lidar reach':>12} {'cells per minute':>17}")
for dmg in (0.0, 0.10, 0.199, 0.20, 0.299, 0.30, 0.493, 0.70, 0.99):
    a = AgentTruth("bench", 100.0, 60.0, 0.0, 1)
    a.damage = dmg
    speed_x = (1.0 - T.DAMAGE_SPEED_LOSS * dmg) if dmg >= T.DAMAGE_SPEED_FROM else 1.0
    rng_x = a.sensor_range_multiplier
    print(f"  {dmg:7.3f} {speed_x:9.3f} {rng_x:9.3f} "
          f"{T.SONAR_RANGE * rng_x:12.2f} {T.LIDAR_RANGE * rng_x:12.2f} "
          f"{T.AGENT_SPEED * speed_x * 60.0:17.1f}")
