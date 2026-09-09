"""Turn the exported belief into MultiMesh instance buffers Godot can memcpy in.

    .venv/Scripts/python.exe spikes/godot/cloud/build_buffers.py --seed 7

Writes data/seed<S>_real.mmbuf and the dense ladder. A .mmbuf is raw little-endian
float32 in Godot's MultiMesh buffer order for TRANSFORM_3D + custom data, 16 floats
per instance:

    row0 = (dp.x, n0.x, n1.x, p0.x)
    row1 = (dp.y, n0.y, n1.y, p0.y)
    row2 = (dp.z, n0.z, n1.z, p0.z)
    custom = (confidence, t_placed, t_fix, source)

Frames. phase1 is 2D in CELLS with +y "up the page" and a separate height in cells
(WALL_POINT_HEIGHT = 2.2 cells = 1.32 m). Godot is Y-up metres. So

    world = (x * 0.6, height * 0.6, -y * 0.6)

which puts a plan-view camera looking down -Y with up = -Z onto phase1's own plan.

THE DENSE LADDER IS AN UPSAMPLE OF THE REAL CLOUD, NOT A MOCK. Each real return
becomes K children scattered in ITS OWN disc plane (so they lie on the surface that
return came off) with a little normal and height jitter, inheriting the parent's fix
displacement, fix time and source. Everything drift, the fix and the spoof do to the
real cloud they therefore do to the dense one, at 2,000,000 points. What it does not
model is a denser sensor seeing surfaces the sparse one missed entirely.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CELL = 0.6
HEAD_M = 0.45        # sensor head height above the floor. A guess; flagged in NOTES.


def load(seed: int):
    d = os.path.join(HERE, "data")
    meta = json.load(open(os.path.join(d, f"seed{seed}.json")))
    n = meta["n_points"]
    a = np.fromfile(os.path.join(d, f"seed{seed}.bin"), dtype=np.float32, offset=16)
    (px0, py0, pz, px1, py1, ox0, oy0, ox1, oy1, conf, t, tfix, src) = a.reshape(13, n)
    return meta, dict(px0=px0, py0=py0, pz=pz, px1=px1, py1=py1, ox0=ox0, oy0=oy0,
                      ox1=ox1, oy1=oy1, conf=conf, t=t, tfix=tfix, src=src)


def frames(c):
    """World-space p0, p1, n0, n1 in metres."""
    p0 = np.column_stack([c["px0"] * CELL, c["pz"] * CELL, -c["py0"] * CELL])
    p1 = np.column_stack([c["px1"] * CELL, c["pz"] * CELL, -c["py1"] * CELL])
    o0 = np.column_stack([c["ox0"] * CELL, np.full(len(p0), HEAD_M), -c["oy0"] * CELL])
    o1 = np.column_stack([c["ox1"] * CELL, np.full(len(p0), HEAD_M), -c["oy1"] * CELL])

    def ray(v):
        """sensor -> hit, UNNORMALISED. Its direction is the disc normal and its LENGTH is
        the range, which the shader needs: the honest disc is the sensor footprint, and a
        footprint is range x beamwidth. See NOTES."""
        out = v.copy()
        bad = (np.linalg.norm(v, axis=1) < 1e-6)
        out[bad] = np.array([0.0, 1.0, 0.0])
        return out

    return p0, p1, ray(o0 - p0), ray(o1 - p1)


def pack(p0, p1, n0, n1, conf, t, tfix, src) -> np.ndarray:
    n = len(p0)
    dp = (p1 - p0).astype(np.float32)
    buf = np.empty((n, 16), dtype=np.float32)
    buf[:, 0] = dp[:, 0]; buf[:, 1] = n0[:, 0]; buf[:, 2] = n1[:, 0]; buf[:, 3] = p0[:, 0]
    buf[:, 4] = dp[:, 1]; buf[:, 5] = n0[:, 1]; buf[:, 6] = n1[:, 1]; buf[:, 7] = p0[:, 1]
    buf[:, 8] = dp[:, 2]; buf[:, 9] = n0[:, 2]; buf[:, 10] = n1[:, 2]; buf[:, 11] = p0[:, 2]
    buf[:, 12] = conf
    buf[:, 13] = t
    buf[:, 14] = tfix
    buf[:, 15] = src
    return buf


def tangents(n):
    up = np.tile(np.array([0.0, 1.0, 0.0]), (len(n), 1))
    flip = np.abs(n[:, 1]) > 0.9
    up[flip] = np.array([1.0, 0.0, 0.0])
    tx = np.cross(up, n)
    tx /= np.maximum(np.linalg.norm(tx, axis=1, keepdims=True), 1e-6)
    ty = np.cross(n, tx)
    return tx, ty


def densify(p0, p1, n0, n1, conf, t, tfix, src, target: int, rng, wall_h_m: float):
    n = len(p0)
    k = max(int(np.ceil(target / n)), 1)
    idx = np.repeat(np.arange(n), k)[:target]
    tx, ty = tangents(n0 / np.maximum(np.linalg.norm(n0, axis=1, keepdims=True), 1e-6))
    m = len(idx)
    # A real sonar/lidar sweep returns a swath off the same surface, so scatter in the
    # PARENT'S OWN disc plane. 0.9 m along the surface is roughly a 1.5-cell patch.
    a = rng.normal(0.0, 0.42, m)
    b = rng.normal(0.0, 0.42, m)
    nz = rng.normal(0.0, 0.018, m)
    walked = (src[idx] > 0.5) & (src[idx] < 1.5)
    # sensed returns fill the height band; walked ones stay on the floor
    b = np.where(walked, b * 0.35, b)
    un = n0 / np.maximum(np.linalg.norm(n0, axis=1, keepdims=True), 1e-6)
    off = (tx[idx] * a[:, None] + ty[idx] * b[:, None] + un[idx] * nz[:, None])
    q0 = p0[idx] + off
    q1 = p1[idx] + off
    q0[:, 1] = np.where(walked, 0.0, np.clip(q0[:, 1] + b * 0.55, 0.0, wall_h_m))
    q1[:, 1] = q0[:, 1]
    cf = np.clip(conf[idx] * rng.normal(1.0, 0.10, m), 0.05, 1.0)
    tt = t[idx] + rng.uniform(-0.35, 0.35, m)
    tt = np.where(tfix[idx] >= 0.0, np.minimum(tt, tfix[idx] - 0.01), tt)
    return q0, q1, n0[idx], n1[idx], cf, np.maximum(tt, 0.0), tfix[idx], src[idx]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--dense", default="100000,500000,1000000,2000000")
    args = ap.parse_args()
    meta, c = load(args.seed)
    p0, p1, n0, n1 = frames(c)
    wall_h_m = meta["wall_point_height_cells"] * CELL
    d = os.path.join(HERE, "data")

    real = pack(p0, p1, n0, n1, c["conf"], c["t"], c["tfix"], c["src"])
    path = os.path.join(d, f"seed{args.seed}_real.mmbuf")
    real.tofile(path)
    print(f"real   {len(real):>9,} instances  {os.path.getsize(path)/1e6:7.1f} MB  {path}")

    rng = np.random.default_rng(7)
    for target in [int(v) for v in args.dense.split(",") if v]:
        q = densify(p0, p1, n0, n1, c["conf"], c["t"], c["tfix"], c["src"],
                    target, rng, wall_h_m)
        buf = pack(*q)
        name = f"dense_{target // 1000}k.mmbuf" if target < 1_000_000 else \
               f"dense_{target // 1_000_000}m.mmbuf"
        path = os.path.join(d, name)
        buf.tofile(path)
        print(f"dense  {len(buf):>9,} instances  {os.path.getsize(path)/1e6:7.1f} MB  {path}")


if __name__ == "__main__":
    main()
