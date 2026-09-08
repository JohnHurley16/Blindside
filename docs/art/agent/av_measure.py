"""Measure the agent probes. Runs on any python with numpy + Pillow (the repo .venv).

  .venv/Scripts/python.exe docs/art/agent/av_measure.py

Two things it reports:

1. EXPOSURE, in the same terms palette.py:luminance uses -- relative luminance with sRGB
   LINEARISED FIRST. palette.py documents doing this on gamma-encoded values as "the easy
   mistake": it compresses the dark end, so a gamma 0.05 threshold is really linear 0.0039,
   which is essentially black. Three of the four earlier probe scripts (im_lum.py,
   lumstats.py, ruins/stats.py) compute on gamma-encoded values and p2_stats.py does not.
   No number from those three is comparable to any number from this one.

2. TEAM SEPARATION AT NINE PIXELS. Box-downsample the frame to a given height, take the
   pixels that are the machine (brighter than the rock behind it), convert to CIELAB and
   report the mean. Two teams separate if dE76 between their means is large; ~2.3 is the
   just-noticeable difference, and below that they are the same object wearing two names.
"""
import sys
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
GAMMA_THRESHOLDS = (0.5, 0.18, 0.05, 0.02)


def srgb_to_linear(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def luminance(a):
    lin = srgb_to_linear(a)
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]


def load(path):
    im = Image.open(path).convert("RGB")
    return np.asarray(im).astype(np.float64) / 255.0


def lin_to_lab(lin):
    """Linear sRGB -> CIELAB (D65)."""
    M = np.array([[0.4124, 0.3576, 0.1805],
                  [0.2126, 0.7152, 0.0722],
                  [0.0193, 0.1192, 0.9505]])
    xyz = lin @ M.T
    white = np.array([0.95047, 1.0, 1.08883])
    t = xyz / white
    d = 6.0 / 29.0
    f = np.where(t > d ** 3, np.cbrt(np.clip(t, 1e-12, None)), t / (3 * d * d) + 4.0 / 29.0)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def box_to_height(a, h):
    """Area-average downsample to height h, preserving aspect."""
    H, W = a.shape[:2]
    w = max(1, int(round(W * h / H)))
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.resize((w, h), Image.BOX)).astype(np.float64) / 255.0


def exposure(path):
    a = load(path)
    lum = luminance(a)
    gl = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]   # gamma-encoded, for contrast
    row = {
        "name": os.path.basename(path),
        "mean": lum.mean(), "median": float(np.median(lum)),
        "blown": (lum > 0.50).mean() * 100,
        "mid": (lum > 0.18).mean() * 100,
        "legible": (lum > 0.05).mean() * 100,
        "black": (lum < 0.02).mean() * 100,
        "gamma_legible": (gl > 0.05).mean() * 100,
    }
    return row


def machine_lab(path, height, frac=0.10):
    """Mean CIELAB of the brightest `frac` of pixels at the given downsample height.
    At nine pixels the machine IS its brightest pixels; that is the whole point."""
    a = box_to_height(load(path), height)
    lin = srgb_to_linear(a)
    lum = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    flat = lum.reshape(-1)
    k = max(1, int(round(flat.size * frac)))
    idx = np.argsort(flat)[-k:]
    sel = lin.reshape(-1, 3)[idx]
    return lin_to_lab(sel.mean(axis=0))


def de76(p, q):
    return float(np.sqrt(((p - q) ** 2).sum()))


def main():
    print("=" * 96)
    print("EXPOSURE  -- relative luminance, sRGB LINEARISED (palette.py convention)")
    print("=" * 96)
    print(f"{'frame':30s} {'mean':>7s} {'median':>7s} {'>0.5':>7s} {'>0.18':>7s} "
          f"{'>0.05':>7s} {'<0.02':>7s} | {'>0.05 if':>9s}")
    print(f"{'':30s} {'':>7s} {'':>7s} {'blown':>7s} {'mid':>7s} "
          f"{'legible':>7s} {'black':>7s} | {'gamma':>9s}")
    print("-" * 96)
    names = sorted(f for f in os.listdir(HERE) if f.endswith(".png"))
    for n in names:
        r = exposure(os.path.join(HERE, n))
        print(f"{r['name']:30s} {r['mean']:7.4f} {r['median']:7.4f} {r['blown']:6.2f}% "
              f"{r['mid']:6.2f}% {r['legible']:6.2f}% {r['black']:6.2f}% | {r['gamma_legible']:8.2f}%")

    print()
    print("=" * 96)
    print("TEAM SEPARATION -- mean CIELAB of the machine's own pixels, by rendered height")
    print("  dE76 < 2.3 = below the just-noticeable difference: the two teams are one object.")
    print("=" * 96)
    pairs = [("value inversion, dust 0.50 (proposed)", "av_05_team_player.png", "av_06_team_rival.png"),
             ("value inversion, dust 0.12 (low dust)", "av_12_team_player_lowdust.png",
              "av_13_team_rival_lowdust.png"),
             ("hue only, as built today", "av_05_team_player.png", "av_07_team_hue.png")]
    for label, fa, fb in pairs:
        pa, pb = os.path.join(HERE, fa), os.path.join(HERE, fb)
        if not (os.path.exists(pa) and os.path.exists(pb)):
            print(f"  {label:32s}  (missing render, skipped)")
            continue
        print(f"\n  {label}")
        print(f"    {'height':>8s}  {'L* a'.rjust(22)}  {'L* b'.rjust(22)}  {'dE76':>7s}")
        for h in (9, 24, 90, 300):
            la, lb = machine_lab(pa, h), machine_lab(pb, h)
            print(f"    {h:6d}px  [{la[0]:6.1f} {la[1]:6.1f} {la[2]:6.1f}]  "
                  f"[{lb[0]:6.1f} {lb[1]:6.1f} {lb[2]:6.1f}]  {de76(la, lb):7.1f}")

    print()
    print("=" * 96)
    print("WEAR -- does the directional mask change anything, and WHERE")
    print("  The existing isotropic mask moves 0.003 mean luminance between wear 0.0 and 0.35.")
    print("  The question is not 'is it different' but 'is it different LOW DOWN', because the")
    print("  whole claim is that wear should have gravity in it.")
    print("=" * 96)
    fa = os.path.join(HERE, "av_03_wear_current.png")
    fb = os.path.join(HERE, "av_04_wear_directed.png")
    if os.path.exists(fa) and os.path.exists(fb):
        a, b = luminance(load(fa)), luminance(load(fb))
        d = np.abs(a - b)
        moved = d > 0.01
        print(f"  whole frame : {moved.mean() * 100:5.2f}% of pixels moved >0.01")
        if moved.any():
            # Frame thirds are the wrong denominator: two thirds of this frame is floor.
            # Measure inside the region the change actually occupies, which is the machine.
            rows = np.where(moved.any(axis=1))[0]
            top, bot = rows.min(), rows.max()
            H = bot - top + 1
            print(f"  change occupies rows {top}-{bot} ({H} px tall) -- that is the machine")
            ys = np.where(moved)[0]
            frac = (ys - top) / max(1, H)
            print(f"  vertical centroid of the change : {frac.mean():.3f} "
                  f"(0.0 = all at the top of the machine, 1.0 = all at its feet)")
            for label, lo, hi in (("upper third", 0.0, 1 / 3), ("middle third", 1 / 3, 2 / 3),
                                  ("lower third", 2 / 3, 1.001)):
                share = ((frac >= lo) & (frac < hi)).mean() * 100
                print(f"    {label:12s}: {share:5.1f}% of all changed pixels")

    print()
    print("=" * 96)
    print("WRECK -- is a collapsed pose readable as DEAD, or only as low?")
    print("=" * 96)
    fa = os.path.join(HERE, "av_11_wreck_ridehonly.png")
    fb = os.path.join(HERE, "av_10_wreck.png")
    if os.path.exists(fa) and os.path.exists(fb):
        for label, f in (("ride height only", fa), ("full collapse   ", fb)):
            a = luminance(load(f))
            lit = a > 0.02
            rows = np.where(lit.any(axis=1))[0]
            cols = np.where(lit.any(axis=0))[0]
            h = (rows.max() - rows.min()) if rows.size else 0
            w = (cols.max() - cols.min()) if cols.size else 0
            print(f"  {label}: lit bounding box {w:4d} x {h:3d} px   "
                  f"aspect {w / max(1, h):5.2f}  (a dead machine is WIDE and LOW)")
    else:
        print("  (missing renders, skipped)")

    print()
    print("=" * 96)
    print("SILHOUETTE -- how much of the frame the loadout changes, backlit")
    print("=" * 96)
    fa, fb = os.path.join(HERE, "av_08_sil_bare.png"), os.path.join(HERE, "av_09_sil_loaded.png")
    if os.path.exists(fa) and os.path.exists(fb):
        a, b = luminance(load(fa)), luminance(load(fb))
        d = np.abs(a - b)
        print(f"  pixels differing by >0.01 linear : {(d > 0.01).mean() * 100:.2f}% of frame")
        print(f"  pixels differing by >0.05 linear : {(d > 0.05).mean() * 100:.2f}% of frame")
        print(f"  bare    frame: {(a < 0.02).mean() * 100:.1f}% true black")
        print(f"  loaded  frame: {(b < 0.02).mean() * 100:.1f}% true black")
    else:
        print("  (missing renders, skipped)")


if __name__ == "__main__":
    main()
