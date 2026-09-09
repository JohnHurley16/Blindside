"""What each post effect actually did to the frame, measured (TRAILER 9).

The cave's cinematic pass found the colour grade taking 14.3% off the mean of
the whole frame through a half-texel LUT lookup error. It did not look like a
bug -- it looked like a moody grade -- and it was caught by MEASURING the
before/after pairs, not by looking at them. This is that measurement, and it is
the reason a port of that code is not finished until it has been run.

Everything is computed on LINEARISED values. ART-DIRECTION 2.9 is explicit that
three of four earlier passes did this on gamma-encoded values and were wrong by
a large factor.

Usage:
    .venv/Scripts/python.exe spikes/godot/surface/paircheck.py DIR [DIR ...]

DIR holds NN_<effect>_off.png / NN_<effect>_on.png pairs, as written by
--cinema=pairs. Also accepts a directory of <name>_{off,on}.png (--cinema=stack).
"""
import sys, os, glob
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))


def linearise(c):
    c = c.astype(np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lum(path):
    im = np.asarray(Image.open(path).convert("RGB"))
    lin = linearise(im)
    return lin, 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]


def bands(y):
    n = y.size
    return (100.0 * np.count_nonzero(y > 0.50) / n,
            100.0 * np.count_nonzero(y > 0.18) / n,
            100.0 * np.count_nonzero(y > 0.05) / n,
            100.0 * np.count_nonzero(y < 0.02) / n)


def one(off_p, on_p, label):
    lo, yo = lum(off_p)
    ln, yn = lum(on_p)
    a = np.asarray(Image.open(off_p).convert("RGB")).astype(np.int16)
    b = np.asarray(Image.open(on_p).convert("RGB")).astype(np.int16)
    d = np.abs(b - a)
    changed = 100.0 * np.count_nonzero(d.max(axis=2) > 0) / (d.shape[0] * d.shape[1])
    changed2 = 100.0 * np.count_nonzero(d.max(axis=2) > 2) / (d.shape[0] * d.shape[1])
    mo, mn = float(yo.mean()), float(yn.mean())
    pct = 100.0 * (mn - mo) / max(mo, 1e-9)
    bo, bn = bands(yo), bands(yn)
    # colour balance, the number PHOTOREAL 3 fought for (B:R = 1.01)
    br_o = float(lo[..., 2].mean() / max(lo[..., 0].mean(), 1e-9))
    br_n = float(ln[..., 2].mean() / max(ln[..., 0].mean(), 1e-9))
    print("%-26s mean %.5f -> %.5f  %+7.2f%%   changed %6.2f%% (>2: %5.2f%%)  max %3d  "
          "B:R %.3f->%.3f" % (label, mo, mn, pct, changed, changed2, int(d.max()), br_o, br_n))
    print("%-26s   blown %5.2f->%5.2f  mid %5.2f->%5.2f  legible %5.2f->%5.2f  black %5.2f->%5.2f"
          % ("", bo[0], bn[0], bo[1], bn[1], bo[2], bn[2], bo[3], bn[3]))
    return pct


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    for root in sys.argv[1:]:
        if not os.path.isabs(root):
            root = os.path.join(HERE, root)
        print("=== %s" % root)
        offs = sorted(glob.glob(os.path.join(root, "*_off.png")))
        if not offs:
            print("  no pairs")
            continue
        tot = 0.0
        for o in offs:
            n = o[:-8] + "_on.png"
            if not os.path.exists(n):
                continue
            tot += one(o, n, os.path.basename(o)[:-8])
        print("  sum of per-effect mean changes: %+.2f%%" % tot)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
