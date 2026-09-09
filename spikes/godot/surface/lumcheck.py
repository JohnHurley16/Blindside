"""The exposure contract on the pit-head (ART-DIRECTION 2.9), before and after
the lens.

Ported from spikes/godot/cave/lumcheck.py. Two things differ and both matter.

1. EVERYTHING IS LINEARISED FIRST. 2.9 is explicit that three of four earlier
   passes computed relative luminance on gamma-encoded values and were wrong by
   a large factor.

2. THE THRESHOLDS IN 2.9's TABLE ARE FOR A LAMP FRAME, AND NOT ONE FRAME HERE
   IS A LAMP FRAME. "> 0.05 legible 3-20%" and "< 0.02 true black >= 70%"
   describe a three-metre pool of carried light in a black room; a yard under an
   overcast sky is legible over 55-72% of frame by construction, and that is the
   contrast the whole design is built on (DESIGN-PRINCIPLES 3, "the surface is
   safe and lit; the cave is not"). Applying the cave's floor to a daylight
   frame would fail every correct picture.

   So the BLOWN ceiling is asserted -- it is the one line of 2.9 that is about
   the sky as much as the lamp -- and the rest is reported as a DELTA: what the
   cinematic layer did to a frame the photoreal pass already signed off. The
   contract this pass has to satisfy is 2.9's actual sentence, "no shot is
   brightened to make it read", which is a statement about CHANGE.

Run:
    .venv/Scripts/python.exe spikes/godot/surface/lumcheck.py DIR_OFF DIR_ON
    .venv/Scripts/python.exe spikes/godot/surface/lumcheck.py DIR
"""
import sys, os, glob
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BLOWN_CEILING = 3.0


def linearise(c):
    c = c.astype(np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def bands(path):
    lin = linearise(np.asarray(Image.open(path).convert("RGB")))
    y = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    n = y.size
    return dict(
        blown=100.0 * np.count_nonzero(y > 0.50) / n,
        mid=100.0 * np.count_nonzero(y > 0.18) / n,
        legible=100.0 * np.count_nonzero(y > 0.05) / n,
        black=100.0 * np.count_nonzero(y < 0.02) / n,
        mean=float(y.mean()))


def resolve(p):
    return p if os.path.isabs(p) else os.path.join(HERE, p)


def single(root):
    files = sorted(glob.glob(os.path.join(root, "*.png")))
    print("%-30s %7s %7s %7s %7s %8s   %s" % (
        "frame", ">0.50", ">0.18", ">0.05", "<0.02", "mean", "verdict"))
    bad = 0
    for f in files:
        b = bands(f)
        v = "BLOWN" if b["blown"] > BLOWN_CEILING else "ok"
        if v != "ok":
            bad += 1
        print("%-30s %6.2f%% %6.2f%% %6.2f%% %6.2f%% %8.4f   %s" % (
            os.path.basename(f)[:-4], b["blown"], b["mid"], b["legible"],
            b["black"], b["mean"], v))
    print("\n%d of %d frames over the 3%% blown ceiling" % (bad, len(files)))
    return bad


def pair(d_off, d_on):
    files = sorted(glob.glob(os.path.join(d_off, "*.png")))
    print("%-30s %17s %17s %17s %9s" % (
        "frame", "blown off->on", "legible off->on", "black off->on", "mean %"))
    worst = 0.0
    bad = 0
    for f in files:
        g = os.path.join(d_on, os.path.basename(f))
        if not os.path.exists(g):
            continue
        a, b = bands(f), bands(g)
        pct = 100.0 * (b["mean"] - a["mean"]) / max(a["mean"], 1e-9)
        worst = min(worst, pct)
        flag = ""
        if b["blown"] > BLOWN_CEILING:
            flag = "  BLOWN"
            bad += 1
        if pct > 0.5:
            flag += "  BRIGHTENED"
        print("%-30s %7.2f%% ->%6.2f%% %7.2f%% ->%6.2f%% %7.2f%% ->%6.2f%% %+8.2f%%%s" % (
            os.path.basename(f)[:-4], a["blown"], b["blown"], a["legible"],
            b["legible"], a["black"], b["black"], pct, flag))
    print("\nlargest mean change: %+.2f%%   frames over the 3%% blown ceiling: %d"
          % (worst, bad))
    return bad


def main():
    if len(sys.argv) == 3:
        return pair(resolve(sys.argv[1]), resolve(sys.argv[2]))
    if len(sys.argv) == 2:
        return single(resolve(sys.argv[1]))
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
