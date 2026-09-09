"""PIL post-processing for the MACHINES board. No Blender.

  .venv/Scripts/python.exe docs/art/vision/machines/ladders.py

Builds, from the renders machines_probe.py wrote and their .bbox.json sidecars:
  nine-pixel/08_ladder_chassis.png    four chassis x six sizes, from the fiction-lit single frames
  nine-pixel/09_ladder_state.png      surveyor / rival / damaged 0.75 / wreck, same ladder
  team/02_ladder_9_24_90.png          player and rival at 9 / 24 / 90 px, from the clear pair
  damage/03_ladder_9_24_90.png        the six damage rungs at 9 / 24 / 90 px
  modules/08_clear_catalogue_sheet.png  side + top orthos stacked, one column per module, labelled
  00_board.png                        every image on the board as a captioned thumbnail

Method is pixel_ladder.py's: crop a square round the machine, LANCZOS down to N px, blow
back up NEAREST to a 120 px cell so every size is compared at the same area. The crop comes
from the sidecar (the projected bounding box of the agent's parts), not from a brightness
threshold -- in a backlit frame the brightest thing is the lamp pool, not the machine.
"""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
if "--dir" in sys.argv:                       # point at another render directory (tests)
    HERE = os.path.abspath(sys.argv[sys.argv.index("--dir") + 1])
CELL = 120
SIZES = [9, 14, 22, 34, 56, 90]
FONT = ImageFont.load_default()


def load(rel):
    p = os.path.join(HERE, rel)
    im = Image.open(p).convert("RGB")
    folder, name = rel.replace("\\", "/").split("/")
    with open(os.path.join(HERE, "_bbox", f"{folder}__{name.replace('.png', '')}.bbox.json")) as f:
        bb = json.load(f)
    return im, bb["agents"]


def crop_square(im, box, pad=0.12):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    s = int(max(w, h) * (1 + 2 * pad))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    X0, Y0 = int(cx - s / 2), int(cy - s / 2)
    out = Image.new("RGB", (s, s), (0, 0, 0))
    src = im.crop((max(0, X0), max(0, Y0), min(im.width, X0 + s), min(im.height, Y0 + s)))
    out.paste(src, (max(0, X0) - X0, max(0, Y0) - Y0))
    return out


def ladder(rows, sizes, out_rel, title):
    """rows: [(label, image, bbox)]"""
    W = 150 + CELL * len(sizes)
    H = 28 + CELL * len(rows)
    sheet = Image.new("RGB", (W, H), (14, 14, 14))
    d = ImageDraw.Draw(sheet)
    d.text((6, 6), title, fill=(200, 200, 200), font=FONT)
    for j, s in enumerate(sizes):
        d.text((150 + j * CELL + 4, 16), f"{s} px", fill=(160, 160, 160), font=FONT)
    for i, (label, im, box) in enumerate(rows):
        sq = crop_square(im, box)
        y = 28 + i * CELL
        d.text((6, y + CELL // 2 - 5), label, fill=(220, 220, 220), font=FONT)
        for j, s in enumerate(sizes):
            small = sq.resize((s, s), Image.LANCZOS)
            big = small.resize((CELL, CELL), Image.NEAREST)
            sheet.paste(big, (150 + j * CELL, y))
    for j in range(1, len(sizes)):
        d.line([(150 + j * CELL, 28), (150 + j * CELL, H)], fill=(60, 60, 60))
    for i in range(1, len(rows)):
        d.line([(150, 28 + i * CELL), (W, 28 + i * CELL)], fill=(60, 60, 60))
    p = os.path.join(HERE, out_rel)
    sheet.save(p)
    print("wrote", out_rel)


def one(rel, label):
    im, bb = load(rel)
    return (label, im, bb[label])


def try_rows(specs):
    rows = []
    for rel, label, shown in specs:
        try:
            im, bb = load(rel)
            rows.append((shown, im, bb[label]))
        except (FileNotFoundError, KeyError) as e:
            print("skip", rel, label, e)
    return rows


def catalogue_sheet():
    side, bbs = load("modules/01_clear_catalogue_side.png")
    top, bbt = load("modules/02_clear_catalogue_top.png")
    W = max(side.width, top.width)
    sheet = Image.new("RGB", (W, side.height + top.height + 40), (18, 18, 18))
    sheet.paste(side, (0, 20))
    sheet.paste(top, (0, 40 + side.height))
    d = ImageDraw.Draw(sheet)
    d.text((6, 4), "bare Surveyor, then each module alone: side (orthographic)", fill=(210, 210, 210), font=FONT)
    d.text((6, 24 + side.height), "the same, from above", fill=(210, 210, 210), font=FONT)
    for label, box in bbs.items():
        cx = (box[0] + box[2]) / 2
        d.text((cx - 4 * len(label) // 2, 6 + side.height), label, fill=(240, 240, 240), font=FONT)
    p = os.path.join(HERE, "modules/08_clear_catalogue_sheet.png")
    sheet.save(p)
    print("wrote modules/08_clear_catalogue_sheet.png")


def board():
    files = sorted(glob.glob(os.path.join(HERE, "*", "*.png")))
    files = [f for f in files if not os.path.basename(f).startswith("00_")]
    TW, TH, COLS = 320, 220, 4
    rows = (len(files) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * TW, rows * TH), (10, 10, 10))
    d = ImageDraw.Draw(sheet)
    for k, f in enumerate(files):
        im = Image.open(f).convert("RGB")
        im.thumbnail((TW - 8, TH - 26))
        x, y = (k % COLS) * TW, (k // COLS) * TH
        sheet.paste(im, (x + 4, y + 4))
        cap = os.path.relpath(f, HERE).replace("\\", "/")
        d.text((x + 4, y + TH - 18), cap[:52], fill=(200, 200, 200), font=FONT)
    p = os.path.join(HERE, "00_board.png")
    sheet.save(p)
    print("wrote 00_board.png", len(files), "images")


if __name__ == "__main__":
    rows = try_rows([("nine-pixel/01_src_scout.png", "scout", "scout"),
                     ("nine-pixel/02_src_surveyor.png", "surveyor", "surveyor"),
                     ("nine-pixel/03_src_hauler.png", "hauler", "hauler"),
                     ("nine-pixel/04_src_swimmer.png", "swimmer", "swimmer")])
    if rows:
        ladder(rows, SIZES, "nine-pixel/08_ladder_chassis.png", "chassis class, fiction-lit (own lamp, backlit), machine height in px")
    rows = try_rows([("nine-pixel/02_src_surveyor.png", "surveyor", "player"),
                     ("nine-pixel/05_src_rival.png", "rival", "rival"),
                     ("nine-pixel/06_src_damaged075.png", "damaged075", "damage 0.75"),
                     ("nine-pixel/07_src_wreck.png", "wreck", "wreck")])
    if rows:
        ladder(rows, SIZES, "nine-pixel/09_ladder_state.png", "state: team, damage, dead -- same frame, same camera")
    rows = try_rows([("team/01_clear_player_vs_rival.png", "player", "player"),
                     ("team/01_clear_player_vs_rival.png", "rival", "rival")])
    if rows:
        ladder(rows, [9, 24, 90], "team/02_ladder_9_24_90.png", "team identity under the CLEAR rig: value inversion, BONE / EMBER")
    rows = try_rows([("damage/01_clear_ladder_side.png", f"d{n:03d}", f"damage {n / 100:.2f}") for n in (0, 20, 30, 50, 75, 100)])
    if rows:
        ladder(rows, [9, 24, 90], "damage/03_ladder_9_24_90.png", "damage rungs at 9 / 24 / 90 px (CLEAR side view)")
    try:
        catalogue_sheet()
    except FileNotFoundError as e:
        print("skip catalogue sheet", e)
    board()
