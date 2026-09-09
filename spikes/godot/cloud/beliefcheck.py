#!/usr/bin/env python
"""Measure what a post effect does to BELIEF, on the two things ART-DIRECTION 8.2
makes absolute rather than on how the frame feels.

    ring        mean |dI/dx| over the luma.  A point cloud at 1.6-3.6 px is
                almost all edge, so this number IS the ring structure: anything
                that merges adjacent returns drops it.
    shadow      pixels that were EXACTLY background in the `off` frame and are
                not in the `on` frame.  A sensor shadow is a void with no
                returns in it, and 8.2 says nothing may ever be drawn into one.
                Any non-zero count here is a rule violation, not a taste call.

    python beliefcheck.py pairs  <dir>
    python beliefcheck.py sbs    <a.png> <b.png> <out.png> [labelA] [labelB]
    python beliefcheck.py cut    <cave.png> <belief.png> <out.png>
    python beliefcheck.py strip  <seqdir> <out.png> [n]
"""
import sys, os, glob
import numpy as np
from PIL import Image, ImageDraw


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32)


def luma(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def modal_bg(a):
    """the frame's most common colour, which in a belief frame is the void"""
    q = (a.astype(np.int32) >> 1)
    key = (q[..., 0] << 16) | (q[..., 1] << 8) | q[..., 2]
    v, c = np.unique(key, return_counts=True)
    k = int(v[np.argmax(c)])
    return np.array([(k >> 16) & 255, (k >> 8) & 255, k & 255], np.float32) * 2.0


def ring_energy(a):
    l = luma(a)
    return float(np.abs(np.diff(l, axis=1)).mean())


def stats(off, on):
    d = np.abs(on - off).max(axis=2)
    changed = float((d > 1.5).mean()) * 100.0
    bg = modal_bg(off)
    void_off = (np.abs(off - bg).max(axis=2) <= 2.0)
    bg_l = float(luma(bg[None, None, :])[0, 0])
    # INTRUSION IS BRIGHTENING, NOT CHANGE. A vignette darkens the whole frame
    # including the void, and darkening a void is not drawing into it -- the
    # first version of this counted that as a 100% violation and was measuring
    # its own threshold. Only light put where the sensor returned nothing
    # counts.
    intruded = void_off & (luma(on) > bg_l + 1.5)
    n_void = int(void_off.sum())
    n_intr = int(intruded.sum())
    lvl = float(luma(on)[intruded].mean() - bg_l) if n_intr else 0.0
    r_off, r_on = ring_energy(off), ring_energy(on)
    return dict(changed=changed, maxd=float(d.max()), meand=float(d.mean()),
                void_pct=100.0 * n_void / void_off.size,
                intr_pct=100.0 * n_intr / max(n_void, 1), intr_lvl=lvl,
                ring_off=r_off, ring_on=r_on,
                ring_ratio=(r_on / r_off if r_off > 0 else 1.0),
                mean_off=float(luma(off).mean()), mean_on=float(luma(on).mean()))


def do_pairs(d):
    rows = []
    for on in sorted(glob.glob(os.path.join(d, "*_on.png"))):
        off = on.replace("_on.png", "_off.png")
        if not os.path.exists(off):
            continue
        name = os.path.basename(on)[:-7]
        rows.append((name, stats(load(off), load(on))))
    hdr = ("%-16s %8s %6s %8s %9s %9s %9s %8s" %
           ("effect", "px chg%", "max", "ring x", "shadow%", "into void", "lvl/255", "mean %"))
    print(hdr)
    print("-" * len(hdr))
    for n, s in rows:
        print("%-16s %7.3f%% %6.0f %8.4f %8.1f%% %8.2f%% %8.2f %+7.1f%%" % (
            n, s["changed"], s["maxd"], s["ring_ratio"], s["void_pct"],
            s["intr_pct"], s["intr_lvl"],
            100.0 * (s["mean_on"] / max(s["mean_off"], 1e-6) - 1.0)))
    print()
    print("ring x    : mean |dI/dx| after / before. < 1 means returns are being merged.")
    print("shadow%   : share of the frame that is exact void in the `off` frame.")
    print("into void : share of THAT void the effect wrote into. Anything above")
    print("            0 is ART-DIRECTION 8.2's absolute rule, broken.")


def _label(im, boxes):
    d = ImageDraw.Draw(im)
    for (x, y, t) in boxes:
        d.rectangle([x - 6, y - 4, x + 9 * len(t), y + 18], fill=(0, 0, 0))
        d.text((x, y), t, fill=(210, 220, 230))
    return im


def do_sbs(a, b, out, la="", lb=""):
    A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    h = min(A.height, B.height)
    A = A.resize((int(A.width * h / A.height), h))
    B = B.resize((int(B.width * h / B.height), h))
    im = Image.new("RGB", (A.width + B.width + 4, h), (255, 255, 255))
    im.paste(A, (0, 0))
    im.paste(B, (A.width + 4, 0))
    if la or lb:
        _label(im, [(16, 16, la), (A.width + 20, 16, lb)])
    im.save(out)
    print("wrote", out, im.size)


def do_cut(cave, bel, out):
    """The alignment test. Cave luma into red, belief luma into cyan; anything
    the two frames agree about lands grey, anything they disagree about is
    coloured. It is the fastest way to see whether the camera is the same."""
    C, B = load(cave), load(bel)
    lc = luma(C)
    lb = luma(B)
    lc = 255.0 * (lc / max(lc.max(), 1e-3)) ** 0.55
    lb = 255.0 * (lb / max(lb.max(), 1e-3)) ** 0.55
    im = np.stack([lc, lb, lb], axis=2).clip(0, 255).astype(np.uint8)
    Image.fromarray(im).save(out)
    print("wrote", out, "(red = cave, cyan = belief)")


def do_strip(seqdir, out, n=6):
    fs = sorted(glob.glob(os.path.join(seqdir, "*.png")))
    if not fs:
        print("no frames in", seqdir)
        return
    idx = [int(round(i * (len(fs) - 1) / (n - 1))) for i in range(n)]
    ims = [Image.open(fs[i]).convert("RGB") for i in idx]
    w = 620
    ims = [im.resize((w, int(im.height * w / im.width))) for im in ims]
    cols = 3
    rows = (len(ims) + cols - 1) // cols
    h = ims[0].height
    sheet = Image.new("RGB", (cols * w + (cols - 1) * 4, rows * h + (rows - 1) * 4), (255, 255, 255))
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % cols) * (w + 4), (k // cols) * (h + 4)))
    sheet.save(out)
    print("wrote", out, sheet.size, "frames", idx)


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "pairs":
        do_pairs(sys.argv[2])
    elif c == "sbs":
        do_sbs(*sys.argv[2:])
    elif c == "cut":
        do_cut(*sys.argv[2:5])
    elif c == "strip":
        do_strip(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 6)
    else:
        print(__doc__)
