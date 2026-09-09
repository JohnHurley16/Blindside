#!/usr/bin/env python3
"""Read the calibration chart back off the PNG and check the physics.

`shots/07_calibration_albedo.png` is rendered orthographically with the tone
mapper set to LINEAR at exposure 1.0 and every material emitting its own ALBEDO
unlit, so the value in the file IS the material's reflectance. The scene writes
`shots/calib_rects.json` at the same moment, giving the pixel rectangle of each
swatch, so nothing here has to guess at the layout.

Photorealism is mostly discipline about these numbers, and a number nobody
re-reads is not a discipline.

    python calib.py
"""
import json
import os
import sys

from lum import read_png, _LIN

HERE = os.path.dirname(os.path.abspath(__file__))
SHOT = os.path.join(HERE, "shots", "07_calibration_albedo.png")
RECTS = os.path.join(HERE, "shots", "calib_rects.json")

# What "plausible" means, and it is not negotiable per material:
#   nothing in the real world reflects less than about 0.008 diffuse (fresh
#   soot is 0.02; a 0.00 albedo is a hole, not a material)
#   nothing reflects more than about 0.92 (fresh snow 0.85, PTFE 0.95, and a
#   metal's F0 is not diffuse albedo -- aluminium's 0.92 is the ceiling here)
FLOOR = 0.008
CEIL = 0.93


def swatch_stats(px, w, nch, r):
    vals = []
    x0, x1 = max(0, r["x0"] + 2), min(w - 1, r["x1"] - 2)
    y0, y1 = max(0, r["y0"] + 2), r["y1"] - 2
    step = max(1, (x1 - x0) // 40)
    ystep = max(1, (y1 - y0) // 40)
    for y in range(y0, y1, ystep):
        for x in range(x0, x1, step):
            i = (y * w + x) * nch
            vals.append(0.2126 * _LIN[px[i]] + 0.7152 * _LIN[px[i + 1]]
                        + 0.0722 * _LIN[px[i + 2]])
    if not vals:
        return None
    vals.sort()
    n = len(vals)
    return {
        "p02": vals[int(n * 0.02)], "mean": sum(vals) / n,
        "p98": vals[int(n * 0.98)], "min": vals[0], "max": vals[-1], "n": n,
    }


def main():
    if not os.path.exists(SHOT) or not os.path.exists(RECTS):
        print("missing %s or %s -- run the testbed with --shots first"
              % (os.path.basename(SHOT), os.path.basename(RECTS)))
        return 2
    meta = json.load(open(RECTS))
    w, h, nch, px = read_png(SHOT)
    if (w, h) != (meta["width"], meta["height"]):
        print("size mismatch: png %dx%d, rects %dx%d"
              % (w, h, meta["width"], meta["height"]))
        return 2

    print("albedo chart: %s, %d swatches, %dx%d" % (
        os.path.basename(SHOT), len(meta["swatches"]), w, h))
    print("plausible band: %.3f .. %.3f linear" % (FLOOR, CEIL))
    print("")
    print("%-22s %7s %7s %7s   %-15s %s" % (
        "material", "p02", "mean", "p98", "claimed", "verdict"))
    print("-" * 92)

    fails, warns = [], []
    for r in meta["swatches"]:
        st = swatch_stats(px, w, nch, r)
        if st is None:
            print("%-22s  swatch is off screen" % r["id"])
            continue
        lo, hi = r["lo"], r["hi"]
        verdict = "ok"
        if st["p98"] > CEIL:
            verdict = "FAIL  above %.2f" % CEIL
            fails.append(r["id"])
        elif st["p02"] < FLOOR:
            verdict = "FAIL  below %.3f" % FLOOR
            fails.append(r["id"])
        elif st["p98"] > hi * 1.20 or st["p02"] < lo * 0.70:
            verdict = "warn  outside its own claim"
            warns.append(r["id"])
        print("%-22s %7.4f %7.4f %7.4f   %.3f - %-7.3f %s" % (
            r["id"], st["p02"], st["mean"], st["p98"], lo, hi, verdict))

    print("")
    if fails:
        print("FAIL: %d material(s) outside plausible albedo: %s"
              % (len(fails), ", ".join(fails)))
        return 1
    if warns:
        print("WARN: %d material(s) outside their own claimed range: %s"
              % (len(warns), ", ".join(warns)))
        return 0
    print("PASS: every material sits inside plausible albedo and inside its claim")
    return 0


if __name__ == "__main__":
    sys.exit(main())
