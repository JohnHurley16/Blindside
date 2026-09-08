"""Luminance histogram of every PNG in a directory, so "too dark" and "unreadable"
stop being opinions. Run with the repo venv (needs numpy + pillow, or numpy alone via
a raw PNG read -- pillow is used if present).

  .venv/Scripts/python.exe docs/art/probes/p2_stats.py <dir>

Columns
  mean/med   relative luminance of the frame, sRGB linearised
  >0.5       blown: the AgX shoulder. The hero renders sit at 17-25% and that is
             the number this art direction exists to bring down
  >0.05      legible: something is there. This is the READABILITY number
  >0.18      mid grey or better: the part of the frame that carries material
  <0.02      true black. The dark is the material, so this should be large
  lit-bbox   the bounding box of everything above 0.05, as a fraction of frame
"""
import os
import sys

import numpy as np

try:
    from PIL import Image
except ImportError:
    Image = None


def lum(a):
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]


def stats(path):
    im = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    y = lum(im)
    m = y > 0.05
    if m.any():
        ys, xs = np.nonzero(m)
        bbox = ((ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1)) / y.size
    else:
        bbox = 0.0
    return dict(mean=y.mean(), med=float(np.median(y)),
                hi=float((y > 0.5).mean()), leg=float((y > 0.05).mean()),
                mid=float((y > 0.18).mean()), blk=float((y < 0.02).mean()), bbox=bbox)


def main(d):
    names = sorted(f for f in os.listdir(d) if f.endswith(".png"))
    print(f"{'render':<24} {'mean':>7} {'med':>7} {'>0.5':>7} {'>0.18':>7} {'>0.05':>7} {'<0.02':>7} {'litbox':>7}")
    for nm in names:
        s = stats(os.path.join(d, nm))
        print(f"{nm[:-4]:<24} {s['mean']:>7.4f} {s['med']:>7.4f} {s['hi']:>6.2%} "
              f"{s['mid']:>6.2%} {s['leg']:>6.2%} {s['blk']:>6.2%} {s['bbox']:>6.1%}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
