#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# BLINDSIDE -- the continuity contact sheet.
#
# TRAILER 11.1 says the trailer follows ONE machine and that nothing enforces
# it. `hero.gd` enforces the DECLARATION -- every shot that names the hero
# names the same chassis, loadout, skin and wear, and a mismatch is rejected
# with the value that caused it. This is the other half: the PICTURE, so that a
# human can check in one look what the validator checks in text.
#
# Each Godot project writes `shots/cinema/hero_boxes.json` (--cinema=hero): for
# every shot that names the hero, the frame to look at and the pixel rectangle
# the machine occupies in it, measured by projecting the mesh AABB through that
# shot's own camera. This crops each of those frames to its own rectangle and
# scales them all to ONE machine height, so the sheet compares machines rather
# than framings. A wrong chassis, a wrong livery, a missing boom or a different
# wear state is then obvious at a glance across the whole cut.
#
#   python spikes/godot/machines/contact_sheet.py
# ---------------------------------------------------------------------------
import io
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
GODOT = os.path.dirname(HERE)
PROJECTS = ["surface", "cave"]

TILE_H = 300          # the machine is scaled to this many pixels tall
PAD = 0.55            # extra crop around the machine, as a fraction of its box
COLS = 4
LABEL_H = 62
GUTTER = 10
BG = (18, 18, 20)
FG = (232, 232, 228)
DIM = (150, 150, 146)


def font(sz):
    for name in ("consola.ttf", "DejaVuSansMono.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, sz)
        except OSError:
            pass
    return ImageFont.load_default()


F_BIG = font(19)
F_SM = font(15)


def collect():
    out = []
    spec = None
    for proj in PROJECTS:
        jp = os.path.join(GODOT, proj, "shots", "cinema", "hero_boxes.json")
        if not os.path.exists(jp):
            print("  (no hero_boxes.json for %s -- run --cinema=hero there)" % proj)
            continue
        d = json.load(io.open(jp, encoding="utf-8"))
        spec = spec or d.get("hero")
        for s in d["shots"]:
            s["project"] = proj
            out.append(s)
    # trailer order, which is the order the cut plays in
    out.sort(key=lambda s: (int(s["trailer"]) if s["trailer"].isdigit() else 999,
                            s["name"]))
    return out, spec


def crop_one(shot):
    png = os.path.join(GODOT, shot["project"], shot["dir"].replace("/", os.sep),
                       "%03d.png" % shot["frame"])
    if not os.path.exists(png):
        return None, "no frame %s" % os.path.basename(png)
    im = Image.open(png).convert("RGB")
    x, y, w, h = shot["rect"]
    if w <= 1 or h <= 1:
        return None, "machine not on screen"
    # square-ish crop centred on the machine, padded, clamped to the frame
    cx, cy = x + w * 0.5, y + h * 0.5
    side = max(w, h) * (1.0 + 2.0 * PAD)
    half = side * 0.5
    box = [cx - half, cy - half, cx + half, cy + half]
    # clamp by SHIFTING rather than by shrinking, so every tile is the same
    # scale relative to the machine
    for i, lim in ((0, 0), (1, 0)):
        if box[i] < lim:
            box[i + 2] += lim - box[i]
            box[i] = lim
    for i, lim in ((2, im.width), (3, im.height)):
        if box[i] > lim:
            box[i - 2] -= box[i] - lim
            box[i] = lim
    box = [max(0, box[0]), max(0, box[1]),
           min(im.width, box[2]), min(im.height, box[3])]
    c = im.crop(tuple(int(round(v)) for v in box))
    # scale so the MACHINE is TILE_H * (1 / (1 + 2*PAD)) tall in the tile
    scale = float(TILE_H) / max(1.0, (box[3] - box[1]))
    tw = max(1, int(round(c.width * scale)))
    th = max(1, int(round(c.height * scale)))
    return c.resize((tw, th), Image.LANCZOS), None


def main():
    shots, spec = collect()
    if not shots:
        print("nothing to sheet")
        return 1
    tiles = []
    for s in shots:
        img, err = crop_one(s)
        tiles.append((s, img, err))

    cols = min(COLS, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    cw = TILE_H + GUTTER
    ch = TILE_H + LABEL_H + GUTTER
    head = 96
    W = GUTTER + cols * cw
    H = head + GUTTER + rows * ch
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)

    d.text((GUTTER + 4, 14), "BLINDSIDE  --  is it the same machine every time?",
           font=F_BIG, fill=FG)
    if spec:
        d.text((GUTTER + 4, 42),
               "declared hero: %s, %s loadout, %s skin, wear %.2f, damage %.2f"
               % (spec["chassis"], spec["loadout"], spec["skin"],
                  spec["wear"], spec["damage"]), font=F_SM, fill=FG)
    d.text((GUTTER + 4, 64),
           "each frame cropped to the machine's own measured bounding box and "
           "scaled to one height, so the tiles compare MACHINES, not framings",
           font=F_SM, fill=DIM)

    for i, (s, img, err) in enumerate(tiles):
        r, c = divmod(i, cols)
        ox = GUTTER + c * cw
        oy = head + GUTTER + r * ch
        d.rectangle([ox, oy, ox + TILE_H - 1, oy + TILE_H - 1], fill=(30, 30, 33))
        if img is not None:
            px = ox + (TILE_H - img.width) // 2
            py = oy + (TILE_H - img.height) // 2
            sheet.paste(img, (px, py))
        else:
            d.text((ox + 10, oy + TILE_H // 2), err or "?", font=F_SM,
                   fill=(220, 120, 110))
        beat = s["trailer"] or "-"
        d.text((ox + 2, oy + TILE_H + 4),
               "%s  shot %s" % (s["project"].upper(), beat), font=F_SM, fill=DIM)
        d.text((ox + 2, oy + TILE_H + 22), s["name"][:34], font=F_SM, fill=FG)
        # the declared identity, on two lines so nothing is cut off: these are
        # the five fields that have to be the same in every tile
        m = s["machine"].replace("hero ", "")
        idpart, _, tail = m.partition(" skin=")
        d.text((ox + 2, oy + TILE_H + 38), idpart[:32], font=F_SM, fill=DIM)
        d.text((ox + 2, oy + TILE_H + 52),
               ("skin=" + tail).replace(" clip=", "  clip=")[:32],
               font=F_SM, fill=DIM)

    out = os.path.join(HERE, "shots", "continuity_sheet.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out)
    print("wrote %s  (%d shots, %d x %d)" % (out, len(tiles), W, H))
    for s, img, err in tiles:
        print("  %-8s beat %-3s %-26s %s"
              % (s["project"], s["trailer"] or "-", s["name"], err or "ok"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
