"""Composites and labels for the machinery vision board. PIL only, no Blender.

Reads the single renders machinery_batch.sh wrote under docs/art/vision/machinery/ and
writes the strips, pairs, the blended slew plan, the labelled three-ages study and the
75-second cycle contact sheet beside them.

  .venv/Scripts/python.exe docs/art/vision/machinery/machinery_sheets.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "C:/Windows/Fonts/consola.ttf"
INK = (236, 230, 218)
BAR = (12, 12, 13)


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def load(rel):
    return Image.open(os.path.join(HERE, rel)).convert("RGB")


def save(img, rel):
    path = os.path.join(HERE, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    print("wrote", rel, img.size)


def caption(img, text, size=22, pad=12):
    """A dark bar under the image with one line of monospace text."""
    f = font(size)
    w, h = img.size
    bar_h = size + 2 * pad
    out = Image.new("RGB", (w, h + bar_h), BAR)
    out.paste(img, (0, 0))
    d = ImageDraw.Draw(out)
    d.text((pad, h + pad - 2), text, font=f, fill=INK)
    return out


def label(img, xy, text, size=22, box=True):
    d = ImageDraw.Draw(img)
    f = font(size)
    x, y = xy
    if box:
        bb = d.textbbox((x, y), text, font=f)
        d.rectangle((bb[0] - 6, bb[1] - 4, bb[2] + 6, bb[3] + 4), fill=(0, 0, 0))
    d.text((x, y), text, font=f, fill=INK)
    return img


def strip(rels, labels, gap=6):
    ims = [load(r) for r in rels]
    h = min(i.size[1] for i in ims)
    ims = [i.resize((int(i.size[0] * h / i.size[1]), h)) for i in ims]
    w = sum(i.size[0] for i in ims) + gap * (len(ims) - 1)
    out = Image.new("RGB", (w, h), BAR)
    x = 0
    for im, lb in zip(ims, labels):
        out.paste(im, (x, 0))
        if lb:
            label(out, (x + 14, 14), lb)
        x += im.size[0] + gap
    return out


def exists(rel):
    return os.path.exists(os.path.join(HERE, rel))


# ---- the wind: clicks 1 / 5 / 9, studio and in the game's light --------------------------------
K = {1: 1956, 5: 2178, 9: 2400}
if all(exists(f"assayer-winding/_click{n}_clear.png") for n in (1, 5, 9)):
    s = strip([f"assayer-winding/_click{n}_clear.png" for n in (1, 5, 9)],
              [f"click {n} of 9   {K[n]} K   hammer {n}/9 up   tank {9 - n}/9 full" for n in (1, 5, 9)])
    save(caption(s, "THE WIND, CLEAR RIG: one source at the winch head ramps 0 -> full in nine 1 s clicks, 1900 K -> 2400 K; "
                    "the tank draws down one ninth per click (sight glass, proposal); a second source at the anvil at a third the output"),
         "assayer-winding/02_clear_clicks_strip.png")
if all(exists(f"assayer-winding/_click{n}_insitu.png") for n in (1, 5, 9)):
    s = strip([f"assayer-winding/_click{n}_insitu.png" for n in (1, 5, 9)],
              [f"click {n}   {K[n]} K" for n in (1, 5, 9)])
    save(caption(s, "THE WIND, IN SITU: the winch head is a beacon (seen from the next chamber, lights little floor); "
                    "the anvil lights the ground the agents stand on. The warning IS the light, the light IS the countdown."),
         "assayer-winding/06_insitu_clicks_strip.png")

# ---- three ages of iron ------------------------------------------------------------------------
if exists("assayer-iron/_three_ages.png"):
    im = load("assayer-iron/_three_ages.png")
    w = im.size[0]
    third = w // 3
    label(im, (third * 0 + 24, 24), "CAST IRON, wet a century", 24)
    label(im, (third * 0 + 24, 56), "(0.075, 0.038, 0.021)  rough 0.86  metallic 0", 18)
    label(im, (third * 0 + 24, 82), "never orange: submerged-and-emerged, a piece of the cave with corners", 16)
    label(im, (third * 1 + 24, 24), "BEARING STEEL, still working", 24)
    label(im, (third * 1 + 24, 56), "(0.52, 0.50, 0.48)  rough 0.30  metallic 1", 18)
    label(im, (third * 1 + 24, 82), "only where something is still rubbing: race, hammer face, chain, track", 16)
    label(im, (third * 2 + 24, 24), "GRAPHITISED, below the waterline", 24)
    label(im, (third * 2 + 24, 56), "black  rough 0.98  metallic 0  sheen", 18)
    label(im, (third * 2 + 24, 82), "intact in silhouette, dead in surface: one material swap on a Z threshold", 16)
    save(caption(im, "THREE AGES OF IRON (ART-DIRECTION 5.2) on one cast knee bracket: fillets, a web, a boss, a parting line. No paint anywhere."),
         "assayer-iron/01_clear_three_ages.png")

# ---- the Bus: dead / live -----------------------------------------------------------------------
if exists("sibling-bus-live/_dead.png") and exists("sibling-bus-live/_live.png"):
    s = strip(["sibling-bus-live/_dead.png", "sibling-bus-live/_live.png"],
              ["DEAD: the sump is a mirror", "LIVE: the water glows faintly (2100 K); the conductor never does"])
    save(caption(s, "THE BUS OVER A SUMP, CLEAR INTERIOR RIG. Same drive, same water; the only difference is the duty cycle. Corona colour/strength are proposals."),
         "sibling-bus-live/03_clear_dead_live_pair.png")

# ---- spent: working / spent ---------------------------------------------------------------------
if exists("spent/_working.png") and exists("spent/_spent.png"):
    s = strip(["spent/_working.png", "spent/_spent.png"],
              ["WORKING: hammer up, tank full, the drip, a dull glow at the drum", "SPENT: boom parked, hammer down, tank drained, anvil dry, no glow ever again"])
    save(caption(s, "A SPENT MACHINE AS A FOUND THING: yields() -> None is a machine that has STOPPED. Readable from across the chamber, permanently; the template for every future 'taken' mark."),
         "spent/03_clear_pair.png")

# ---- plans: the probe's straight-down camera lands with +X down the frame; turn them so
# +X is right and +Y is up, the way a plan is read -----------------------------------------------
def plan(rel):
    return load(rel).rotate(90, expand=True)


if exists("assayer-dormant/_plan_raw.png"):
    im = plan("assayer-dormant/_plan_raw.png")
    label(im, (24, 24), "PLAN, +X right, +Y up, 1.2 m grid. Boom at 35 deg; tank on -Y; bolt ring r 2.04 m; Surveyor at the footing", 18)
    save(caption(im, "THE ASSAYER IN PLAN (THE-MACHINERY 2.1 at 0.6 m/cell): footing legs at 120 deg to r 1.56 m, boom 4.20 m, counterweight 1.32 m, "
                     "the old service platform at r 2.04 m."),
         "assayer-dormant/02_clear_plan.png")

# ---- the slew: two bearings in plan, 36 deg apart --------------------------------------------------
if exists("assayer-slew/_plan_a.png") and exists("assayer-slew/_plan_b.png"):
    a = plan("assayer-slew/_plan_a.png")
    b = plan("assayer-slew/_plan_b.png")
    im = Image.blend(a, b, 0.5)
    label(im, (24, 24), "THE INDEX STEP, in plan: the boom at 41.5 deg (this cycle) and 5.5 deg (next), blended", 22)
    label(im, (24, 56), "-36 deg per cycle, always the same direction. Learnable from two slews.", 18)
    save(caption(im, "THE SLEW: 36 deg in 3 s, seventeen seconds before anything is dangerous. Horizontal rotation is the tell; nothing emits."),
         "assayer-slew/01_clear_index_plan.png")

# ---- the 75-second cycle as one sheet ---------------------------------------------------------------
tiles = [
    ("assayer-dormant/06_insitu_lamp.png", "0-54 s  LISTENING", "nothing emits; one drip every two seconds onto the anvil"),
    ("assayer-slew/02_insitu_blur.png", "54-57 s  THE SLEW", "the arm swings 36 deg and stops; the bearing race catches the visitor's lamp"),
    ("assayer-dormant/06_insitu_lamp.png", "57-62 s  LOCKED", "five seconds of stillness after a movement: it has decided something"),
    ("assayer-winding/03_insitu_click1.png", "62 s  CLICK 1", "1956 K, 1/9 output"),
    ("assayer-winding/04_insitu_click5.png", "66 s  CLICK 5", "2178 K, 5/9 output; tank 4/9"),
    ("assayer-winding/05_insitu_click9.png", "70 s  CLICK 9", "2400 K, full; tank empty"),
    ("assayer-firing/02_insitu_strike_machine_height.png", "71.0 s  THE FIRE", "one frame at ~4x, 4000 K: the only white light in the game"),
    ("assayer-firing/03_insitu_decay_2s_lobe.png", "71-75 s  LETHAL, then decay", "the shock is in the ground; the lobe is a decal in the silt, never a glow"),
]
if all(exists(t[0]) for t in tiles):
    TW, TH = 460, 300
    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    gap = 8
    head = 70
    W = cols * TW + (cols + 1) * gap
    H = head + rows * (TH + 52 + gap) + gap + 60
    out = Image.new("RGB", (W, H), BAR)
    d = ImageDraw.Draw(out)
    d.text((gap + 6, 16), "THE 75-SECOND CYCLE  (THE-MACHINERY.md 3, ART-DIRECTION.md 5.4)  --  firings at t = 41 mod 75", font=font(26), fill=INK)
    # the timeline bar
    x0, x1, y = gap + 6, W - gap - 6, head - 12
    d.rectangle((x0, y - 3, x1, y + 3), fill=(60, 58, 54))
    for t, col in ((0, (60, 58, 54)), (54, (120, 110, 95)), (57, (120, 110, 95)), (62, (255, 122, 47)), (71, (255, 214, 165)), (75, (60, 58, 54))):
        x = x0 + (x1 - x0) * t / 75.0
        d.rectangle((x - 2, y - 9, x + 2, y + 9), fill=col)
        d.text((x - 8, y + 12), str(t), font=font(14), fill=INK)
    d.rectangle((x0 + (x1 - x0) * 62 / 75.0, y - 3, x0 + (x1 - x0) * 71 / 75.0, y + 3), fill=(255, 122, 47))
    d.rectangle((x0 + (x1 - x0) * 71 / 75.0, y - 3, x0 + (x1 - x0) * 75 / 75.0, y + 3), fill=(200, 60, 48))
    for i, (rel, title, sub) in enumerate(tiles):
        im = load(rel)
        im.thumbnail((TW, TH))
        c, r = i % cols, i // cols
        x = gap + c * (TW + gap)
        yy = head + 20 + r * (TH + 52 + gap)
        out.paste(im, (x + (TW - im.size[0]) // 2, yy + (TH - im.size[1]) // 2))
        d.text((x + 4, yy + TH + 6), title, font=font(20), fill=INK)
        d.text((x + 4, yy + TH + 30), sub, font=font(14), fill=(190, 184, 172))
    d.text((gap + 6, H - 44), "every tile is an in-situ frame from this board: lit only by the visitor's lamp, its running lights, and the two hot points",
           font=font(16), fill=(190, 184, 172))
    save(out, "assayer-cycle/01_cycle_sheet.png")

# ---- the chamber rule, captioned ------------------------------------------------------------------
if exists("assayer-chamber/_cutaway.png"):
    im = load("assayer-chamber/_cutaway.png")
    label(im, (24, 24), "6.6 m mast under an ~11 m crown, 21 m across; the Surveyor at the footing is 0.57 m tall", 20)
    save(caption(im, "THE CHAMBER RULE (ART-DIRECTION 5.5): a chamber that holds something worth seeing must be taller than the 4.8 m passages that "
                     "reach it, or the mast does not fit and nothing in it is seen from outside. Cutaway by camera near-clip; studio light; not the game."),
         "assayer-chamber/01_clear_cutaway.png")

print("sheets done")
