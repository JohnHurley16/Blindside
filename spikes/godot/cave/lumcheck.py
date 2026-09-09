"""The exposure contract, checked (ART-DIRECTION 2.9).

Reads every PNG in shots/ and prints the LINEARISED luminance bands. The doc is
explicit that three of the four earlier passes computed this on gamma-encoded
values and were therefore wrong by a large factor, so this linearises first.

Targets for a lamp frame:
    > 0.50  blown     <= 3%
    > 0.18  mid        1 - 25%
    > 0.05  legible    3 - 20%   (below 3% is unplayable)
    < 0.02  true black >= 70%

Run:  .venv/Scripts/python.exe spikes/godot/cave/lumcheck.py
"""
import sys, os, glob
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "shots")


def linearise(c):
    c = c.astype(np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def bands(path):
    im = np.asarray(Image.open(path).convert("RGB"))
    lin = linearise(im)
    y = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    n = y.size
    return dict(
        blown=100.0 * np.count_nonzero(y > 0.50) / n,
        mid=100.0 * np.count_nonzero(y > 0.18) / n,
        legible=100.0 * np.count_nonzero(y > 0.05) / n,
        black=100.0 * np.count_nonzero(y < 0.02) / n,
        mean=float(y.mean()),
    )


def main():
    files = sorted(glob.glob(os.path.join(SHOTS, "*.png")))
    if not files:
        print("no shots")
        return 1
    print("%-24s %7s %7s %7s %7s %8s   %s" % (
        "shot", ">0.50", ">0.18", ">0.05", "<0.02", "mean", "verdict"))
    bad = 0
    for f in files:
        b = bands(f)
        v = []
        if b["blown"] > 3.0:
            v.append("BLOWN")
        if b["legible"] < 3.0:
            v.append("too dark")
        if b["legible"] > 20.0:
            v.append("unsourced light")
        if b["black"] < 70.0:
            v.append("not enough black")
        if v:
            bad += 1
        print("%-24s %6.2f%% %6.2f%% %6.2f%% %6.2f%% %8.4f   %s" % (
            os.path.basename(f)[:-4], b["blown"], b["mid"], b["legible"],
            b["black"], b["mean"], ", ".join(v) if v else "ok"))
    print("\n%d of %d frames outside the contract" % (bad, len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
