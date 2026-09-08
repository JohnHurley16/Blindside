"""The ten-pixel test.

The art lens is "readable first". A match is watched at CAMERA_WIDE_CELLS = 225 across
a 200x120 cave, where SPECTATOR-DISPLAY 6.4 measures a machine glyph at NINE PIXELS.
This asks the only question that matters at that size: with the hero renders resampled
down a ladder, at what height does each read survive -- chassis class, loadout, team,
alive-or-dead -- and what is actually carrying it.

Outputs, into docs/art/probes/:
  ladder_chassis.png   four chassis, six sizes, on the frame's own ground
  ladder_state.png     loaded / bare / rival / salvage, same ladder
  and a table on stdout: at each height, the machine's contrast against the rock behind
  it, and the fraction of the machine's remaining light that is emissive.

No Blender needed; this runs on the PNGs the render probes already made.
"""
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SIZES = [9, 14, 22, 34, 56, 90]        # machine height in pixels


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def load(name):
    im = Image.open(os.path.join(HERE, name)).convert("RGB")
    return np.asarray(im).astype(np.float32) / 255.0


def machine_bbox(a, floor_pct=88.0):
    """The machine is the brightest connected mass in a frame whose rock is dark.
    Threshold at a high percentile, then take the bounding box of what is left,
    ignoring stray specks by requiring a row/column to hold several lit pixels."""
    l = lum(a)
    t = np.percentile(l, floor_pct)
    m = l > max(t, 0.02)
    rows = np.where(m.sum(axis=1) > 4)[0]
    cols = np.where(m.sum(axis=0) > 4)[0]
    if len(rows) == 0 or len(cols) == 0:
        return None
    return rows[0], rows[-1] + 1, cols[0], cols[-1] + 1


def crop_square(a, bb, pad=0.12):
    r0, r1, c0, c1 = bb
    h, w = r1 - r0, c1 - c0
    s = int(max(h, w) * (1 + 2 * pad))
    cr, cc = (r0 + r1) // 2, (c0 + c1) // 2
    R0, C0 = cr - s // 2, cc - s // 2
    out = np.zeros((s, s, 3), np.float32)
    sr0, sc0 = max(0, R0), max(0, C0)
    sr1, sc1 = min(a.shape[0], R0 + s), min(a.shape[1], C0 + s)
    out[sr0 - R0:sr1 - R0, sc0 - C0:sc1 - C0] = a[sr0:sr1, sc0:sc1]
    return out


def down(a, n):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.resize((n, n), Image.LANCZOS)).astype(np.float32) / 255.0


def strip(names, labels, path, sizes=SIZES):
    """One row per source, one column per size, each cell nearest-neighbour blown up to
    a common 120 px so the eye compares the same information at the same area."""
    CELL = 120
    tiles = []
    for nm in names:
        a = load(nm)
        bb = machine_bbox(a)
        c = crop_square(a, bb)
        row = []
        for s in sizes:
            d = down(c, s)
            big = np.asarray(Image.fromarray((np.clip(d, 0, 1) * 255).astype(np.uint8))
                             .resize((CELL, CELL), Image.NEAREST)).astype(np.float32) / 255.0
            row.append(big)
        tiles.append(np.concatenate(row, axis=1))
    grid = np.concatenate(tiles, axis=0)
    # 1 px rules so the cells are countable
    for i in range(1, len(sizes)):
        grid[:, i * CELL] = 0.18
    for j in range(1, len(names)):
        grid[j * CELL, :] = 0.18
    Image.fromarray((np.clip(grid, 0, 1) * 255).astype(np.uint8)).save(os.path.join(HERE, path))
    print(f"wrote {path}   rows={labels}  cols={sizes}")


def report(names, labels):
    print(f"{'source':<22}{'bbox px':>10}{'size':>7}{'machine L':>11}"
          f"{'ground L':>10}{'contrast':>10}{'emissive share':>16}")
    for nm, lb in zip(names, labels):
        a = load(nm)
        bb = machine_bbox(a)
        c = crop_square(a, bb)
        for s in (9, 22, 56):
            d = down(c, s)
            l = lum(d)
            # the machine is the top third of luminance in the tile; ground is the bottom half
            hi = l > np.percentile(l, 66)
            lo = l < np.percentile(l, 50)
            ml, gl = l[hi].mean(), l[lo].mean()
            # emissive share: how much of the machine's light sits in pixels that are
            # both bright AND saturated (a coloured light), vs neutral lit paint
            mx = d.max(axis=2)
            mn = d.min(axis=2)
            sat = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0.0)
            emis = (l > 0.25) & (sat > 0.22)
            share = l[emis].sum() / max(l[hi].sum(), 1e-6)
            print(f"{lb:<22}{str(bb[1]-bb[0])+'x'+str(bb[3]-bb[2]):>10}{s:>7}"
                  f"{ml:>11.3f}{gl:>10.3f}{ml-gl:>10.3f}{share:>16.2f}")


if __name__ == "__main__":
    chassis = ["01_scout_default.png", "02_surveyor_default.png",
               "03_hauler_default.png", "04_swimmer_default.png"]
    clab = ["scout", "surveyor", "hauler", "swimmer"]
    state = ["02_surveyor_default.png", "05_surveyor_bare.png",
             "06_surveyor_loud.png", "08_wreck_salvage.png"]
    slab = ["surveyor loaded", "surveyor bare", "rival (team_b)", "salvage w1.0"]
    dark = [n for n in ("14_dark_shaft.png", "13_dark_assayer.png", "21_econ.png",
                        "22_econ_quiet.png") if os.path.exists(os.path.join(HERE, n))]
    strip(chassis, clab, "ladder_chassis.png")
    strip(state, slab, "ladder_state.png")
    print()
    report(chassis, clab)
    print()
    report(state, slab)
    if dark:
        strip(dark, dark, "ladder_dark.png")
        print()
        report(dark, [d[:20] for d in dark])
