"""Frame exposure statistics, so 'readable' is a number rather than an opinion."""
import sys, os
import numpy as np
from PIL import Image

print("%-26s %6s %6s %7s %7s %8s" % ("frame", "mean", "med", ">0.5", ">0.05", "<0.02"))
for p in sys.argv[1:]:
    if not os.path.exists(p):
        print("%-26s MISSING" % os.path.basename(p))
        continue
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    print("%-26s %6.3f %6.3f %6.2f%% %6.2f%% %7.2f%%" % (
        os.path.basename(p), lum.mean(), np.median(lum),
        100 * (lum > 0.5).mean(), 100 * (lum > 0.05).mean(), 100 * (lum < 0.02).mean()))
