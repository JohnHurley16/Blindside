"""Composite sheets for the cave board: PIL only, no Blender. Reads the sorted frames
in cave/<concept>/ and writes labelled rows/pairs beside them, plus one pure-PIL strip
(the six depth cues). Run after sort_into_concepts.py:

    .venv/Scripts/python.exe sheets.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PAD, BAR = 12, 34
BG = (18, 18, 20)
FG = (225, 220, 210)
DIM = (140, 135, 125)


def font(size=18):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _load(concept, name, width=None):
    p = os.path.join(HERE, concept, name)
    im = Image.open(p).convert("RGB")
    if width and im.width != width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    return im


def row(concept, names, labels, out, title=None, per_w=None, cols=None):
    """Frames side by side (wrapping to `cols` per row), a label bar under each."""
    ims = [_load(concept, n, per_w) for n in names]
    cols = cols or len(ims)
    w, h = ims[0].width, ims[0].height
    rows = (len(ims) + cols - 1) // cols
    top = BAR + PAD if title else PAD
    W = PAD + cols * (w + PAD)
    H = top + rows * (h + BAR + PAD)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    f, ft = font(17), font(20)
    if title:
        d.text((PAD, 8), title, fill=FG, font=ft)
    for i, (im, lab) in enumerate(zip(ims, labels)):
        r, c = divmod(i, cols)
        x = PAD + c * (w + PAD)
        y = top + r * (h + BAR + PAD)
        sheet.paste(im, (x, y))
        d.text((x + 4, y + h + 8), lab, fill=FG, font=f)
    sheet.save(os.path.join(HERE, concept, out))
    print("wrote", concept, out, sheet.size)


def caption(concept, name, text, out, width=1200):
    im = _load(concept, name, width)
    f = font(18)
    lines = text.split("\n")
    H = im.height + PAD * 2 + 26 * len(lines)
    sheet = Image.new("RGB", (im.width, H), BG)
    sheet.paste(im, (0, 0))
    d = ImageDraw.Draw(sheet)
    for i, ln in enumerate(lines):
        d.text((PAD, im.height + PAD + 26 * i), ln, fill=FG if i == 0 else DIM, font=f)
    sheet.save(os.path.join(HERE, concept, out))
    print("wrote", concept, out, sheet.size)


def depth_cues_strip(out):
    """B11: one BFS field, six consumers. A diagram, not a render."""
    W, H = 1400, 560
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    ft, f, fs = font(24), font(18), font(15)
    d.text((PAD, 10), "DEPTH — one BFS field from the player's shaft, six consumers (ART-DIRECTION §7)", fill=FG, font=ft)
    x0, x1, y = 60, W - 60, 80
    # the axis: shallow -> deep as darkness
    for i in range(x0, x1):
        t = (i - x0) / (x1 - x0)
        v = int(120 * (1 - 0.55 * t) + 10)
        d.line([(i, y), (i, y + 26)], fill=(int(v * 1.22), int(v * 0.98), int(v * 0.72)))
    d.text((x0, y + 32), "SHALLOW  natural karst, dry, a bit of rail", fill=FG, font=f)
    d.text((x1 - 330, y + 32), "DEEP  machine ground, wet, lit by machines", fill=FG, font=f)
    cues = [
        ("1  worked", "natural CA blobs -> cut horseshoe drive with sets, gutter, bolt line -> stopes, launders, pump chambers. Straight lines increase with depth."),
        ("2  iron in frame", "none -> bolt lines, rails, trays -> pipework, then machines. The gauge a player reads without being taught."),
        ("3  water", "wet walls -> tide mark -> standing water -> sump. Deeper has highlights: depth is where the specular is."),
        ("4  darkness", "rock albedo x (1 - 0.55 depth). Deep rock is wet, and wet rock is much darker."),
        ("5  the marks get younger", "shallow plates corroded and half-buried in flowstone; deep plates sharp. The mine worked downward and got better as it went."),
        ("6  the beacon chain thins", "BEACON_DROP_EVERY_CELLS = 45: three or four of your own beacons in a shallow frame; past the machinery, none, and the last is behind you."),
    ]
    yy = y + 80
    for k, (h, body) in enumerate(cues):
        d.text((x0, yy), h, fill=FG, font=f)
        d.text((x0 + 250, yy), body, fill=DIM, font=fs)
        yy += 48
    d.text((x0, H - 60), "and the inversion: deeper is darker (more water, no shaft) and more lit (more machines, and machines are the only world light).", fill=FG, font=fs)
    d.text((x0, H - 36), "The dangerous place is the visible place. Depth is never altitude.", fill=FG, font=fs)
    im.save(os.path.join(HERE, "cave-depth", out))
    print("wrote cave-depth", out, im.size)


def main():
    # B2: the four width classes in one row, same rig, same Surveyor
    row("cave-width",
        ["01_clear_section_crawl.png", "02_clear_section_narrow.png", "03_clear_section_passage.png", "04_clear_section_hall.png"],
        ["CRAWL  2-3 cells, 1.5 x 1.3 m here", "NARROW  3-4 cells, 2.1 x 2.2 m", "PASSAGE  4-5 cells, 2.7 x 3.2 m", "HALL  >= 5 cells, 3.9 x 5.0 m"],
        "09_sheet_four_classes.png", title="Passages by width class - same rock, same rig, same 0.77 m Surveyor, 0.60 m gauge on the floor (class metres are a guess: CHASSIS-TIMING D5)",
        per_w=640, cols=2)
    # B5: above and below the line, same drive
    row("cave-underwater", ["01_clear_above.png", "02_clear_below.png"],
        ["ABOVE the line: the same drive, the water a mirror", "BELOW the line: scatter 0.35, absorption off red, light dies in 4-6 m"],
        "06_sheet_above_below.png", title="Below the waterline - one drive, one lamp, the medium changes", per_w=640)
    # B6: stopped / walking / blinded
    row("cave-silt", ["01_insitu_stopped.png", "02_insitu_walking.png", "03_insitu_blinded.png"],
        ["STOPPED  rest 0.008: no beam, only the pool", "WALKING  ~0.05 behind and around it: the beam appears", "0.15  self-blinding"],
        "05_sheet_three_densities.png", title="Silt - the beam is only visible when the agent has stirred it. Moving makes you visible twice.", per_w=460)
    # B8: the negative concept, captioned as the rule
    row("cave-magnetic", ["01_insitu_noisy.png", "02_insitu_deposit.png"],
        ["magnetically NOISY rock (false find)", "rock over a TRUE deposit"],
        "03_sheet_the_rule.png",
        title="Magnetic character: NOTHING visible, ever. Same lamp, same rock family. If noisy rock glowed, the magnetometer would be redundant.", per_w=640)
    # B11: the two triptychs
    row("cave-depth", ["01_clear_shallow.png", "02_clear_middle.png", "03_clear_deep.png"],
        ["SHALLOW  natural, dry, beacons", "MIDDLE  the cut drive: sets, rails, plates", "DEEP  machine ground: pump, Bus, launder, water"],
        "07_sheet_clear_triptych.png", title="Depth, CLEAR - same rig, same Surveyor (the deep frame's camera is pulled back to hold a 12 m room)", per_w=460)
    row("cave-depth", ["04_insitu_shallow.png", "05_insitu_middle.png", "06_insitu_deep.png"],
        ["SHALLOW  lamp + three of your own beacons", "MIDDLE  lamp + rails", "DEEP  lamp + the winch glow round the corner, no beacons"],
        "08_sheet_insitu_triptych.png", title="Depth, IN-SITU - the same three places in the game's own light", per_w=460)
    depth_cues_strip("09_six_cues.png")
    # B7: the swatch wall, labelled
    caption("cave-rock", "01_clear_swatches.png",
            "Rock type is four scalars, never a hue. Columns: fracture 3 / 8 / 14 (bump 0.3 / 0.6 / 0.9). Rows: bedding contrast low (top) / high (bottom).\n"
            "Absorbent rock = friable, tight, spalled (right); reflective = dense, planar, blocky (left). One warm buff family throughout.",
            "05_sheet_swatches_labelled.png")
    caption("cave-rock", "02_clear_three_values.png",
            "The three rock values in the game: dry lit #9E8B74 (left), wet above the line #796C5B (middle), submerged #554D46 (right, under a water block).",
            "06_sheet_three_values_labelled.png")
    # B4: the section, labelled by band
    caption("cave-waterline", "01_clear_section.png",
            "Waterline section, cut down the passage axis: dry rock above / 0.12 m tide-mark crust (albedo x1.7, matte) / the surface (IOR 1.33, roughness 0.02) / submerged rock (albedo x0.6, roughness 0.10).\n"
            "The Surveyor stands on the bank at the crust line; the ruler is 1.2 m.",
            "06_sheet_section_labelled.png")


if __name__ == "__main__":
    main()
