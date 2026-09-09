"""PIL-only board images for the 'found' group. No Blender.

  .venv/Scripts/python.exe docs/art/vision/found/_probes/icons_and_ladder.py

  discovery/03_block_icons.png   a mock of the block-icon row the policy editor would show:
                                 a discovery's OWN representation is an item icon in the
                                 editor (DESIGN-PRINCIPLES 1: Minecraft items), never a
                                 world object. Hollow = predicate, filled = action, in the
                                 display's node colours; the two just-found blocks carry the
                                 silhouette of the plant that yielded them.  PROPOSAL.
  wreck/08_nine_pixel.png        wreck/06_situ_pair resampled down the display's ladder
                                 (machine height 90 .. 9 px): a flat thing where a tall
                                 thing should be.
  map/05_belief_inset.png        the belief inset of the 2:23 spectator frame, cropped and
                                 enlarged 3x: the map the player actually gets.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = r"C:/Users/jackh/documents/programming/Blindside"
OUT = os.path.join(ROOT, "docs/art/vision/found")
sys.path.insert(0, ROOT)
from phase1.view import palette as PAL  # noqa: E402


def rgb(c, a=1.0):
    return tuple(int(round(v * 255 * a)) for v in c[:3])


def font(size):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------------------
def block_icons():
    W, H = 1200, 420
    im = Image.new("RGB", (W, H), rgb(PAL.PANEL))
    d = ImageDraw.Draw(im)
    f_t = font(22)
    f_s = font(15)
    f_h = font(26)
    d.text((28, 18), "BLOCKS  --  the item row of the policy editor (mock, proposal)", fill=rgb(PAL.PRIMARY), font=f_h)
    d.text((28, 52), "a discovery is a transaction; what it yields is one of these. Hollow asks, filled acts. "
                     "The two on the right were just taken from the Assayer.", fill=rgb(PAL.SECONDARY), font=f_s)
    preds = [("unexplored\nbranch?", "day one"), ("uncertainty\n> theta", "day one"), ("carrying\ncargo?", "day one"),
             ("machinery\naudible?", "phase 1"), ("deposit\nleft?", "phase 1")]
    acts = [("take\nbranch", "day one"), ("return to\nbeacon", "day one"), ("fetch from\na deposit", "phase 1"),
            ("freeze until\nit passes", "phase 1")]
    found = [("hear the\nground", "FOUND 5:41", True), ("ride the\nroad", "FOUND 5:41", False)]
    x, y, s, gap = 28, 100, 108, 18

    def tile(x, y, label, sub, hollow, hot=False):
        fill = rgb(PAL.NODE_TEST_HOT if hot else (PAL.NODE_FILL if hollow else PAL.NODE_ACTION_FILL))
        edge = rgb(PAL.NODE_EDGE_HOT if hot else (PAL.NODE_EDGE if hollow else PAL.NODE_ACTION_EDGE))
        d.rounded_rectangle((x, y, x + s, y + s), radius=12, fill=fill, outline=edge, width=2 if hollow else 4)
        # the glyph: a hollow diamond asks, a filled chevron acts
        cx, cy = x + s / 2, y + 36
        if hollow:
            d.polygon([(cx, cy - 16), (cx + 16, cy), (cx, cy + 16), (cx - 16, cy)], outline=rgb(PAL.GHOST), width=2)
        else:
            d.polygon([(cx - 16, cy - 12), (cx + 2, cy - 12), (cx + 16, cy), (cx + 2, cy + 12), (cx - 16, cy + 12)], fill=rgb(PAL.CARGO))
        d.multiline_text((x + 10, y + 58), label, fill=rgb(PAL.PRIMARY), font=f_s, spacing=2)
        d.text((x, y + s + 6), sub, fill=rgb(PAL.TERTIARY), font=f_s)

    d.text((x, y - 24), "PREDICATES", fill=rgb(PAL.SECONDARY), font=f_t)
    for lab, sub in preds:
        tile(x, y, lab, sub, True)
        x += s + gap
    x += 30
    d.text((x, y - 24), "ACTIONS", fill=rgb(PAL.SECONDARY), font=f_t)
    for lab, sub in acts:
        tile(x, y, lab, sub, False)
        x += s + gap
    # found: the plant's silhouette on the card, LIE-amber edge while new
    x0 = x + 30
    d.text((x0, y - 24), "JUST FOUND", fill=rgb(PAL.LIE), font=f_t)
    for lab, sub, hollow in found:
        tile(x0, y, lab, sub, hollow, hot=True)
        # a tiny Assayer: mast, boom, footing, in the rock's own colour
        mx, my = x0 + s - 26, y + 14
        d.line([(mx, my), (mx, my + 34)], fill=rgb(PAL.ASSAYER_MAST), width=3)
        d.line([(mx - 14, my + 8), (mx + 4, my + 8)], fill=rgb(PAL.ASSAYER_IRON), width=3)
        d.polygon([(mx - 9, my + 40), (mx + 9, my + 40), (mx, my + 30)], fill=rgb(PAL.ASSAYER_IRON))
        x0 += s + gap
    # the rule this is read against
    yy = y + s + 46
    d.text((28, yy), "Rules it obeys:", fill=rgb(PAL.SECONDARY), font=f_t)
    lines = ["a block is added by data, forever; the editor's row grows; nothing is written over a fixed set by name",
             "the world side of a discovery is the STATION (a control surface), the POSE (head down, 80 s) and the MARK "
             "(a stopped machine); the item side is this icon and nothing else",
             "colours are the display's own node values (palette.py); accents mean one thing each -- CARGO is the objective, "
             "LIE-amber is 'new / unverified', never red"]
    for i, ln in enumerate(lines):
        d.text((28, yy + 34 + i * 26), "-  " + ln, fill=rgb(PAL.TERTIARY), font=f_s)
    path = os.path.join(OUT, "discovery", "03_block_icons.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    print("WROTE", path)


# ---------------------------------------------------------------------------------------
def nine_pixel(src, out, heights=(90, 56, 34, 22, 14, 9)):
    """pixel_ladder.py's method on the pair frame (wreck/06_situ_pair, 960x600): two fixed
    crops -- the standing machine at left, the wreck at right -- resampled together so the
    STANDING machine is h px tall, shown 3x nearest above and 1x below. Same scene, same
    scale, so the wreck's height at every rung is honest."""
    im = Image.open(src).convert("RGB")
    sx, sy = im.width / 960.0, im.height / 600.0
    healthy = im.crop((int(80 * sx), int(180 * sy), int(300 * sx), int(410 * sy)))
    wreck = im.crop((int(520 * sx), int(180 * sy), int(860 * sx), int(410 * sy)))
    stand_h = 205 * sy                      # the standing machine's height in the crop, px
    W = 1180
    canvas = Image.new("RGB", (W, 470), (6, 8, 11))
    d = ImageDraw.Draw(canvas)
    f = font(16)
    d.text((16, 12), "the nine-pixel test: a standing machine (left) and a wreck (right), backlit by a third machine, "
                     "resampled to the display's ladder", fill=(147, 162, 177), font=f)
    d.text((16, 34), "(standing-machine height in px; 1x above, the small rungs 3x nearest below). A flat thing where "
                     "a tall thing should be -- what the display's X means.", fill=(147, 162, 177), font=f)
    def rung(h):
        scale = h / stand_h
        tiles = [crop.resize((max(1, int(round(crop.width * scale))), max(1, int(round(crop.height * scale)))), Image.LANCZOS)
                 for crop in (healthy, wreck)]
        gap = max(2, int(6 * scale))
        row_w = tiles[0].width + gap + tiles[1].width
        row_h = max(t.height for t in tiles)
        small = Image.new("RGB", (row_w, row_h), (6, 8, 11))
        small.paste(tiles[0], (0, row_h - tiles[0].height))
        small.paste(tiles[1], (tiles[0].width + gap, row_h - tiles[1].height))
        return small

    # row 1: every rung at 1x, the way the display would show it
    x, y = 16, 70
    for h in heights:
        small = rung(h)
        canvas.paste(small, (x, y + 104 - small.height))
        d.text((x, y + 110), f"{h} px", fill=(147, 162, 177), font=f)
        x += small.width + 22
    # row 2: the four small rungs at 3x nearest, so the pixels can be counted
    x, y = 16, 220
    d.text((x, y - 24), "the same four small rungs at 3x nearest:", fill=(86, 98, 111), font=f)
    for h in heights[2:]:
        small = rung(h)
        big = small.resize((small.width * 3, small.height * 3), Image.NEAREST)
        canvas.paste(big, (x, y + 120 - big.height))
        d.text((x, y + 126), f"{h} px x3", fill=(147, 162, 177), font=f)
        x += big.width + 26
    canvas = canvas.crop((0, 0, W, 380))
    canvas.save(out)
    print("WROTE", out)


def belief_inset(src, out):
    im = Image.open(src).convert("RGB")
    # the inset lives top-right of the main view at 1600x900 scaled to 2000x1125: crop by ratio
    W, H = im.size
    box = (int(W * 0.593), int(H * 0.058), int(W * 0.812), int(H * 0.283))
    crop = im.crop(box)
    big = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
    canvas = Image.new("RGB", (big.width, big.height + 44), (6, 8, 11))
    canvas.paste(big, (0, 44))
    d = ImageDraw.Draw(canvas)
    d.text((12, 10), "ITS MAP at 2:23, the inset the display draws, 3x: this and only this is what a policy or a "
                     "pendant screen may show. Truth is elsewhere.", fill=(147, 162, 177), font=font(15))
    canvas.save(out)
    print("WROTE", out)


if __name__ == "__main__":
    which = sys.argv[1:] or ["icons", "ladder", "inset"]
    if "icons" in which:
        block_icons()
    if "ladder" in which:
        src = os.path.join(OUT, "wreck", "06_situ_pair.png")
        if os.path.exists(src):
            nine_pixel(src, os.path.join(OUT, "wreck", "08_nine_pixel.png"))
        else:
            print("no pair frame yet")
    if "inset" in which:
        belief_inset(os.path.join(OUT, "map", "snap_143.png"), os.path.join(OUT, "map", "05_belief_inset.png"))
