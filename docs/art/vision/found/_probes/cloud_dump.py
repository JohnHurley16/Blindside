"""Dump one agent's BELIEF (its point cloud, trail, pose, known beacons) and the TRUTH
geometry around it, at a list of sim times, for cloud_scene.py to render in Blender.

    .venv/Scripts/python.exe docs/art/vision/found/_probes/cloud_dump.py --seed 7 --times 143,300,341

Reads phase1 only. Writes <here>/data/seed<S>_t<T>.npz. Nothing in phase1 is modified.

Two frames are written side by side on purpose: the cloud is in the agent's BELIEF frame
and the cave grid is TRUTH. The renderer draws both in one world so the drift shows as a
shape offset from the wall it was measured off -- that is the picture ART-DIRECTION 8.2
asks for. The truth pose is included only to place the rendered machine; the cloud never
sees it (it never can: PointCloud stores x, y, z, confidence, t, source and nothing else).

Ray direction: PointCloud does NOT store the sensor->hit direction. It is reconstructed
here as (point - believed pose at the point's timestamp), using the belief trail, which is
the only origin the belief layer knows. That reconstruction is a guess and is flagged.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

ROOT = r"C:/Users/jackh/documents/programming/Blindside"
sys.path.insert(0, ROOT)

from phase1 import tuning as T                    # noqa: E402
from phase1.match.sim import Sim                  # noqa: E402
from phase1.truth import cave                     # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def dump(sim: Sim, name: str, path: str) -> None:
    b = sim.beliefs[name]
    a = sim._world.agents[name]               # truth: for placing the rendered machine only
    n = b.cloud.n
    trail = np.array(b.trail, dtype=float)    # (x, y, t) believed
    # origin of each point: the believed pose at the point's timestamp (nearest trail t)
    tt = trail[:, 2]
    idx = np.searchsorted(tt, b.cloud.t[:n], side="right") - 1
    idx = np.clip(idx, 0, len(trail) - 1)
    ox, oy = trail[idx, 0], trail[idx, 1]
    beacons = np.array([(kb.x, kb.y) for kb in b.beacons.values()], dtype=float).reshape(-1, 2)
    truth_trail = np.array(sim.truth_trail[name], dtype=float).reshape(-1, 3)
    np.savez(path,
             t=sim.t,
             cloud_xyz=np.column_stack([b.cloud.x[:n], b.cloud.y[:n], b.cloud.z[:n]]),
             cloud_conf=b.cloud.confidence[:n],
             cloud_t=b.cloud.t[:n],
             cloud_source=b.cloud.source[:n],       # 0 sonar 1 near 2 false 3 lidar
             cloud_origin=np.column_stack([ox, oy]),
             occupied=b.cloud.occupied,
             belief_pose=np.array([b.x, b.y, b.theta]),
             belief_ellipse=np.array(b.ellipse()),
             belief_trail=trail,
             beacons_believed=beacons,
             truth_pose=np.array([a.x, a.y, a.heading]),          # heading is already radians
             truth_trail=truth_trail,
             grid=cave.GRID,                        # 0 rock 1 dry 2 flooded, (H, W), y up
             grid_cell=0.6,
             grid_offset=np.array([60.0, 60.0, 2.0]),
             chambers=np.array([(c[0], c[1], c[2]) for c in cave.CHAMBERS.values()], dtype=float),
             )
    print(f"  {os.path.basename(path)}: t={sim.t:.1f} points={n} "
          f"belief=({b.x:.1f},{b.y:.1f}) truth=({a.x:.1f},{a.y:.1f}) "
          f"err={np.hypot(a.x - b.x, a.y - b.y):.1f} cells sigma={b.sigma_pos():.1f} "
          f"trail={len(trail)} beacons={len(beacons)} doing={sim.policies[name].doing}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=T.SEED)
    ap.add_argument("--times", default="143,300,341")
    ap.add_argument("--agent", default="player")
    args = ap.parse_args()
    times = sorted(float(v) for v in args.times.split(","))
    out = os.path.join(HERE, "data")
    os.makedirs(out, exist_ok=True)
    sim = Sim(args.seed)
    print(f"seed {args.seed}: running to {times}")
    for at in times:
        while not sim.over and sim.t < at:
            sim.step()
            if sim.tick % 10 == 0:
                sim.record_truth_trail()
        dump(sim, args.agent, os.path.join(out, f"seed{args.seed}_t{int(at):03d}.npz"))


if __name__ == "__main__":
    main()
