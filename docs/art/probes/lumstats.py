"""Luminance statistics for any probe render, same measure the first pass used."""
import sys, os
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
print(f"{'render':<26}{'mean':>8}{'median':>9}{'>0.5':>8}{'>0.05':>8}{'<0.02':>8}")
for nm in sys.argv[1:]:
    p = nm if os.path.exists(nm) else os.path.join(HERE, nm)
    if not os.path.exists(p):
        print(f"{nm:<26}  (missing)"); continue
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float32)/255.
    l = 0.2126*a[...,0]+0.7152*a[...,1]+0.0722*a[...,2]
    print(f"{os.path.basename(nm):<26}{l.mean():>8.3f}{np.median(l):>9.3f}"
          f"{(l>0.5).mean():>8.2%}{(l>0.05).mean():>8.2%}{(l<0.02).mean():>8.2%}")
