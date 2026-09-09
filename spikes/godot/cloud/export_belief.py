"""Export one phase1 match's BELIEF as a scrubable point cloud, for the Godot spike.

    .venv/Scripts/python.exe spikes/godot/cloud/export_belief.py --seed 7

Reads phase1; modifies nothing in it.  Two hooks are installed on the classes at
runtime (`Belief._add_point`, `PointCloud.relax`) so that the two things the belief
object does NOT store can be captured:

  1. the sensor origin of every return, taken at the instant the point is added --
     the believed pose right then.  `PointCloud` stores x, y, z, confidence, t and
     source and nothing else, so a disc "facing back along its ray" (ART 8.2) is not
     drawable from Belief as it stands.  This is the flagged limitation in
     docs/art/vision/found/NOTES.md and it is a Phase-3 Belief change, not an art one.
  2. every relax(): which points a fix moved and where it moved them to.

THE FINDING THAT MAKES THE RENDERER TRIVIAL, and it is asserted below rather than
assumed: `relax()` moves points with `t > correction.epoch_t`, and `epoch_t` is the
PREVIOUS fix's time.  Point times are monotonic in index, so the moved set is always
a contiguous suffix, and every point is therefore moved by AT MOST ONE fix -- the
first fix after it was placed.  After that it is frozen for ever, which is exactly
ART 8.2's "old returns are never re-registered".

So a point needs two positions and one timestamp, and the whole of drift / fix /
spoof is a per-vertex switch.  No CPU work per scrub frame, at any point count.

Output (spikes/godot/cloud/data/), and the split is deliberate:

  BELIEF ONLY -- everything the live view is allowed to read
    seed<S>.json      fixes, beacons, believed trail, time bounds
    seed<S>.bin       "BSCLOUD1" + n:u32 + pad + 13 float32 arrays of length n

  TRUTH -- replay only, and a live client must never be handed these
    seed<S>_truth.json   the true pose over time
    seed<S>_grid.bin     true occupancy, H*W bytes (0 rock, 1 dry, 2 flooded)

PROCEDURAL-AND-GODOT 2.1 asks for exactly this shape and asks for it as an absolute:
the live client receives no path to truth at all. Here that is two files, and
cloud_root.gd opens the truth pair only when the mode is `truth` or `both`.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys

import numpy as np

ROOT = r"C:/Users/jackh/documents/programming/Blindside"
sys.path.insert(0, ROOT)

from phase1 import tuning as T                       # noqa: E402
from phase1.belief.belief import Belief              # noqa: E402
from phase1.belief.point_cloud import PointCloud     # noqa: E402
from phase1.match.sim import Sim                     # noqa: E402
from phase1.truth import cave                        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MAGIC = b"BSCLOUD1"


class Capture:
    """Everything the renderer needs that Belief does not keep."""

    def __init__(self, agent: str) -> None:
        self.agent = agent
        self.ox: list[float] = []          # sensor origin at placement (believed frame)
        self.oy: list[float] = []
        self.moved_once = None             # np.ndarray[bool], asserts the suffix finding
        self.n_moves: list[int] = []
        self.rewrites: list[tuple[float, int, int]] = []   # (t, k, n)


def install(cap: Capture, belief: Belief) -> None:
    raw_add = Belief._add_point
    raw_relax = PointCloud.relax

    def add_point(self, r, t):                       # type: ignore[no-untyped-def]
        if self is belief:
            cap.ox.append(self.x)
            cap.oy.append(self.y)
        raw_add(self, r, t)

    def relax(self, correction):                     # type: ignore[no-untyped-def]
        if self is not belief.cloud:
            raw_relax(self, correction)
            return
        n = self.n
        mask = self.t[:n] > correction.epoch_t
        k = int(np.argmax(mask)) if mask.any() else n
        # the moved set must be the contiguous suffix [k, n)
        assert bool(mask[k:].all()) and not bool(mask[:k].any()), "moved set is not a suffix"
        # and the origins ride along with the trail, by the same correction
        if k < n:
            oxa = np.array(cap.ox[k:n])
            oya = np.array(cap.oy[k:n])
            nx, ny = correction.apply(oxa, oya, self.t[k:n])
            cap.ox[k:n] = nx.tolist()
            cap.oy[k:n] = ny.tolist()
        raw_relax(self, correction)
        cap.rewrites.append((float(correction.epoch_t + correction.span), k, n))

    Belief._add_point = add_point                    # type: ignore[method-assign]
    PointCloud.relax = relax                         # type: ignore[method-assign]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=T.SEED)
    ap.add_argument("--agent", default="player")
    args = ap.parse_args()

    sim = Sim(args.seed)
    belief = sim.beliefs[args.agent]
    cap = Capture(args.agent)
    install(cap, belief)

    # per-point first position, captured the tick it is added, before any fix touches it
    p0x: list[float] = []
    p0y: list[float] = []
    o0x: list[float] = []
    o0y: list[float] = []
    seen = 0
    truth_by_t: list[tuple[float, float, float, float]] = []

    while not sim.over:
        sim.step()
        if sim.tick % 5 == 0:
            sim.record_truth_trail()
            a = sim._world.agents[args.agent]
            truth_by_t.append((sim.t, a.x, a.y, a.heading))
        n = belief.cloud.n
        if n > seen:
            p0x.extend(belief.cloud.x[seen:n].tolist())
            p0y.extend(belief.cloud.y[seen:n].tolist())
            o0x.extend(cap.ox[seen:n])
            o0y.extend(cap.oy[seen:n])
            seen = n

    n = belief.cloud.n
    c = belief.cloud
    px0 = np.array(p0x[:n], dtype=np.float32)
    py0 = np.array(p0y[:n], dtype=np.float32)
    ox0 = np.array(o0x[:n], dtype=np.float32)
    oy0 = np.array(o0y[:n], dtype=np.float32)
    px1 = c.x[:n].astype(np.float32)
    py1 = c.y[:n].astype(np.float32)
    ox1 = np.array(cap.ox[:n], dtype=np.float32)
    oy1 = np.array(cap.oy[:n], dtype=np.float32)
    pz = c.z[:n].astype(np.float32)
    conf = c.confidence[:n].astype(np.float32)
    pt = c.t[:n].astype(np.float32)
    src = c.source[:n].astype(np.float32)

    # the time each point was rewritten: the first rewrite whose range covers it
    tfix = np.full(n, -1.0, dtype=np.float32)
    for t_fix, k, m in cap.rewrites:
        idx = np.arange(k, min(m, n))
        fresh = idx[tfix[idx] < 0.0]
        tfix[fresh] = t_fix
    twice = 0
    for t_fix, k, m in cap.rewrites:
        idx = np.arange(k, min(m, n))
        twice += int(np.count_nonzero(tfix[idx] != t_fix))
    assert twice == 0, f"{twice} points were moved by more than one fix"

    out = os.path.join(HERE, "data")
    os.makedirs(out, exist_ok=True)
    bin_path = os.path.join(out, f"seed{args.seed}.bin")
    with open(bin_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<II", n, 0))
        for arr in (px0, py0, pz, px1, py1, ox0, oy0, ox1, oy1, conf, pt, tfix, src):
            f.write(np.ascontiguousarray(arr, dtype=np.float32).tobytes())

    grid = cave.GRID.astype(np.uint8)
    with open(os.path.join(out, f"seed{args.seed}_grid.bin"), "wb") as f:
        f.write(grid.tobytes())

    spoof = [e for e in sim._world.events if "spoof" in str(e).lower()]
    spoof_t = None
    spoof_detail: dict = {}
    for e in sim._world.events:
        d = getattr(e, "detail", None) or getattr(e, "data", None) or {}
        if getattr(e, "kind", "") == "spoof" or "spoof" in str(e).lower():
            spoof_t = float(e.t)
            spoof_detail = {k: (float(v) if isinstance(v, (int, float)) else str(v))
                            for k, v in (d.items() if hasattr(d, "items") else [])}
            break

    meta = {
        "seed": args.seed,
        "agent": args.agent,
        "n_points": int(n),
        "t_end": float(sim.t),
        "cell_m": 0.6,
        "wall_point_height_cells": float(T.WALL_POINT_HEIGHT),
        "result": str(sim.result),
        "grid_w": int(grid.shape[1]),
        "grid_h": int(grid.shape[0]),
        "spoof_t": spoof_t,
        "fixes": [{"t": f.t, "beacon": f.beacon_id, "pre": [f.pre_x, f.pre_y],
                   "post": [f.post_x, f.post_y], "jump": f.jump,
                   "dtheta": f.dtheta, "sigma_before": f.sigma_before,
                   "surprise": f.surprise} for f in belief.fixes],
        "beacons": [{"id": k, "x": v.x, "y": v.y, "t": v.t_placed,
                     "anchor": bool(v.truth_anchor)} for k, v in belief.beacons.items()],
        "belief_trail": [[round(x, 3), round(y, 3), round(t, 2)] for x, y, t in belief.trail],
        "rewrites": [{"t": t, "k": k, "n": m} for t, k, m in cap.rewrites],
    }
    with open(os.path.join(out, f"seed{args.seed}.json"), "w") as f:
        json.dump(meta, f)
    # Truth, in its own file, so that "the live view never reads truth" is a fact about
    # which files are open and not a fact about anyone's self-discipline.
    with open(os.path.join(out, f"seed{args.seed}_truth.json"), "w") as f:
        json.dump({"truth_pose": [[round(t, 2), round(x, 3), round(y, 3), round(h, 4)]
                                  for t, x, y, h in truth_by_t],
                   "spoof": spoof_detail,
                   "spoof_events": [str(e) for e in spoof]}, f)

    err = [(t, math.hypot(x - bx, y - by))
           for (t, x, y, _), (bx, by, bt) in
           zip(truth_by_t[:0], [])]  # placeholder; error printed below per fix
    print(f"seed {args.seed}: {n} points, t_end {sim.t:.1f}s, result {sim.result}")
    print(f"  {len(belief.fixes)} fixes, {len(cap.rewrites)} rewrites, "
          f"{int(np.count_nonzero(tfix >= 0))} of {n} points moved exactly once, "
          f"{int(np.count_nonzero(tfix < 0))} never moved")
    for f_ in belief.fixes:
        print(f"    fix t={f_.t:7.1f} {f_.beacon_id:>10s} jump {f_.jump:6.1f} cells "
              f"surprise {f_.surprise:5.1f}x dtheta {math.degrees(f_.dtheta):6.1f} deg")
    print(f"  spoof at t={spoof_t} {spoof_detail}")
    for e in spoof:
        print(f"    {e}")
    print(f"  wrote {bin_path} ({os.path.getsize(bin_path)/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
