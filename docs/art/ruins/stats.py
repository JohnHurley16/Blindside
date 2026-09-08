"""Luminance statistics for a render, in the same terms the first evidence pass used:
mean, median, and the fraction of the frame above 0.5 (blown), above 0.05 (legible)
and below 0.02 (true black).

  python docs/art/ruins/stats.py docs/art/ruins/*.png docs/art/probes/14_dark_shaft.png
"""
import sys, glob
import numpy as np
from PIL import Image

paths = []
for a in sys.argv[1:]:
    paths.extend(sorted(glob.glob(a)))
print(f"{'render':<34} {'mean':>7} {'median':>7} {'>0.5':>7} {'>0.05':>7} {'<0.02':>7}")
for p in paths:
    im = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0
    lum = 0.2126 * im[..., 0] + 0.7152 * im[..., 1] + 0.0722 * im[..., 2]
    print(f"{p.split(chr(92))[-1].split('/')[-1]:<34} "
          f"{lum.mean():7.3f} {np.median(lum):7.3f} "
          f"{float((lum > 0.5).mean()) * 100:6.2f}% {float((lum > 0.05).mean()) * 100:6.2f}% "
          f"{float((lum < 0.02).mean()) * 100:6.2f}%")
