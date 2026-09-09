"""PIL sheets for the teaching / mood board: screen mocks, palette strips, light-source sheets,
the corridor plan, and the contact sheets assembled from the renders.

  .venv/Scripts/python.exe docs/art/vision/teaching/teaching_sheets.py --stage pre  --snaps <dir>
  .venv/Scripts/python.exe docs/art/vision/teaching/teaching_sheets.py --stage post

`pre` needs the phase1 / phase2 snapshot PNGs (python -m phase2 --snap, python -m phase1 --teach --snap,
python -m phase1 --snap 143,341,480) in --snaps. `post` needs the Blender renders in this directory.
No Blender. Every number here is read off ART-DIRECTION.md / phase1/view/palette.py or stated as a guess in NOTES.md.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

ap = argparse.ArgumentParser()
ap.add_argument("--stage", default="pre")
ap.add_argument("--snaps", default=None)
ap.add_argument("--seed", type=int, default=104)
A = ap.parse_args()

FONT_DIR = Path("C:/Windows/Fonts")


def font(size, mono=False, bold=False):
    name = "consola.ttf" if mono else ("bahnschrift.ttf" if not bold else "arialbd.ttf")
    try:
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except OSError:
        return ImageFont.load_default()


# ---- palette (phase1/view/palette.py + ART-DIRECTION.md 3.1 / 5.2) -----------------------------
def hx(rgb):
    return "#%02X%02X%02X" % tuple(int(round(c * 255)) for c in rgb)


def lum(rgb):
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def lin2srgb(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def to8(rgb):
    return tuple(int(round(max(0, min(1, c)) * 255)) for c in rgb)


def kelvin(T):
    """Planckian locus -> linear sRGB, normalised so the brightest channel is 1. (Kim et al. cubic
    fit for xy, then XYZ -> sRGB.) Good to a few percent between 1667 K and 25000 K."""
    t = T
    if t <= 4000:
        x = -0.2661239e9 / t ** 3 - 0.2343589e6 / t ** 2 + 0.8776956e3 / t + 0.179910
    else:
        x = -3.0258469e9 / t ** 3 + 2.1070379e6 / t ** 2 + 0.2226347e3 / t + 0.240390
    if t <= 2222:
        y = -1.1063814 * x ** 3 - 1.34811020 * x ** 2 + 2.18555832 * x - 0.20219683
    elif t <= 4000:
        y = -0.9549476 * x ** 3 - 1.37418593 * x ** 2 + 2.09137015 * x - 0.16748867
    else:
        y = 3.0817580 * x ** 3 - 5.87338670 * x ** 2 + 3.75112997 * x - 0.37001483
    Y = 1.0
    X = x * Y / y
    Z = (1 - x - y) * Y / y
    r = 3.2406 * X - 1.5372 * Y - 0.4986 * Z
    g = -0.9689 * X + 1.8758 * Y + 0.0415 * Z
    b = 0.0557 * X - 0.2040 * Y + 1.0570 * Z
    m = max(r, g, b)
    return (max(r, 0) / m, max(g, 0) / m, max(b, 0) / m)


def kelvin_srgb(T):
    return tuple(lin2srgb(c) for c in kelvin(T))


VOID = (0.024, 0.031, 0.043)
PANEL = (0.043, 0.055, 0.075)
RULE = (0.102, 0.129, 0.169)
ROCK, ROCK_LIT, FLOOR, WATER = (0.082, 0.067, 0.051), (0.227, 0.180, 0.133), (0.165, 0.133, 0.098), (0.086, 0.125, 0.180)
BONE, EMBER, WARM_DIM = (0.949, 0.902, 0.824), (1.000, 0.478, 0.184), (0.478, 0.400, 0.314)
SENSED, WALKED, GHOST, COOL_DIM = (0.388, 0.839, 0.969), (0.180, 0.282, 0.329), (0.624, 0.910, 1.000), (0.227, 0.322, 0.376)
HAZARD, LIE, CARGO, KILL, HURT = (1.0, 0.31, 0.847), (1.0, 0.824, 0.247), (0.31, 0.878, 0.541), (1.0, 0.231, 0.188), (0.878, 0.435, 0.376)
PRIMARY, SECONDARY, TERTIARY = (0.949, 0.961, 0.976), (0.576, 0.635, 0.694), (0.337, 0.384, 0.435)
# world values (ART-DIRECTION 3.1, 5.2, 2.1), given there as LINEAR reflectances / light colours
DRY_LIT, WET_ABOVE, SUBMERGED, TIDE, SCOURED = (0.340, 0.260, 0.175), (0.190, 0.150, 0.105), (0.090, 0.075, 0.062), (0.520, 0.470, 0.400), (0.420, 0.360, 0.280)
CAST_IRON, BEARING, GRAPHITISED = (0.075, 0.038, 0.021), (0.52, 0.50, 0.48), (0.012, 0.012, 0.012)
SKY12000 = (0.60, 0.74, 1.00)
LAMP = (1.00, 0.98, 0.95)
RESIDUAL = (1.00, 0.72, 0.42)
PALE_SHELL, GRAPHITE = (0.66, 0.63, 0.57), (0.050, 0.052, 0.058)
PORCELAIN = (0.92, 0.92, 0.90)
SALVAGE_LIGHT = (0.85, 0.72, 0.55)
SPOIL_WET = tuple(c * 0.6 for c in DRY_LIT)
HARDSTANDING = (0.14, 0.13, 0.115)
KIT_DARK = (0.11, 0.115, 0.12)
JACKET = (0.045, 0.055, 0.05)
UNDERWATER = (0.05, 0.075, 0.09)


def strip(path, title, swatches, sub=None, w=1400):
    """One palette strip: title, N swatches each labelled hex / linear luminance / meaning.
    `swatches` = [(name, rgb, meaning, is_linear)]. Linear values are gamma-encoded for display and
    the hex printed is the DISPLAY hex; the luminance printed is relative luminance, linearised."""
    n = len(swatches)
    sw = (w - 40) // n
    h = 330
    im = Image.new("RGB", (w, h), to8(VOID))
    d = ImageDraw.Draw(im)
    d.text((20, 14), title, fill=to8(PRIMARY), font=font(26))
    if sub:
        d.text((20, 46), sub, fill=to8(SECONDARY), font=font(16))
    y0 = 80
    for i, (name, rgb, meaning, is_linear) in enumerate(swatches):
        disp = tuple(lin2srgb(c) for c in rgb) if is_linear else rgb
        x = 20 + i * sw
        d.rectangle((x, y0, x + sw - 6, y0 + 130), fill=to8(disp), outline=to8(RULE))
        d.text((x + 6, y0 + 140), name, fill=to8(PRIMARY), font=font(17))
        d.text((x + 6, y0 + 163), hx(disp) + ("  lin" if is_linear else "  display"), fill=to8(SECONDARY), font=font(12, mono=True))
        d.text((x + 6, y0 + 180), ("%.3f %.3f %.3f" % rgb) if is_linear else ("Y = %.3f" % lum(disp)), fill=to8(SECONDARY), font=font(12, mono=True))
        # wrap the meaning
        words = meaning.split()
        lines, cur = [], ""
        for wd in words:
            if d.textlength(cur + " " + wd, font=font(13)) > sw - 14:
                lines.append(cur)
                cur = wd
            else:
                cur = (cur + " " + wd).strip()
        lines.append(cur)
        for k, ln in enumerate(lines[:5]):
            d.text((x + 6, y0 + 200 + k * 16), ln, fill=to8(TERTIARY), font=font(13))
    im.save(path)
    print("wrote", path)


def palette_strips():
    strip(HERE / "h1_01_palette-surface.png", "SURFACE  -  the pit-head, the only place with sky",
          [("sky, overcast", SKY12000, "the shaft's own 12000 K: the surface light IS the shaft light (guess)", True),
           ("wet iron", CAST_IRON, "the dead works: headframe, collar, engine. no paint, never orange", True),
           ("spoil, wet", SPOIL_WET, "the flat the course stands on: dry buff x0.6 for rain", True),
           ("hardstanding", HARDSTANDING, "setts in front of the winding house, puddled (guess)", True),
           ("pale shell", PALE_SHELL, "the player's machine, just pale in daylight", True),
           ("graphite", GRAPHITE, "the chassis; the rival's shell", True),
           ("kit, dark", KIT_DARK, "pendant, terminal, crates: new polymer, matte (guess)", True),
           ("jacket", JACKET, "the player: waxed cotton, hooded, no face (guess)", True),
           ("BONE", BONE, "player emissives, strength <= 3; invisible in daylight", False),
           ("EMBER", EMBER, "rival emissives; never seen on this surface", False)],
          sub="Linear values from ART-DIRECTION 3.1 / 5.2 shown gamma-encoded; the last two are palette.py display values. Nothing here is a hue the cave does not have.")
    strip(HERE / "h1_02_palette-shaft.png", "SHAFT  -  the descent, the only cold light",
          [("12000 K disc", SKY12000, "the sky seen from below; the only daylight in the cave", True),
           ("VOID", VOID, "outside everything, and everything never sensed", False),
           ("wet rock", WET_ABOVE, "the shaft chamber walls, wet above the line", True),
           ("pale shell", PALE_SHELL, "the last pale thing in the kibble", True),
           ("timber", (0.10, 0.07, 0.045), "the sets in the top 6 m of the shaft (guess)", True),
           ("bearing steel", BEARING, "the new cable, the sheave groove: the one bright thing", True)],
          sub="The descent is the one moment a machine is lit from above.")
    strip(HERE / "h1_03_palette-shallow.png", "SHALLOW  -  natural karst with a bit of rail in it",
          [("dry, lit", DRY_LIT, "rock at the light end of the bedding ramp, in the lamp", True),
           ("scoured floor", SCOURED, "bare fresh-fractured bedrock: the Assayer's floor", True),
           ("wet, above the line", WET_ABOVE, "albedo x0.6, roughness 0.10", True),
           ("work lamp", LAMP, "white for every team; 50 deg, 8-10 deg down", True),
           ("WARM_DIM pilot", WARM_DIM, "a beacon's pilot: never team-coloured; useful to 3.6 m, seen to 20", False),
           ("BONE strip", BONE, "player running lights, or their retroreflection", False),
           ("ROCK_LIT (display)", ROCK_LIT, "the display's lit-rock anchor: where the two registers agree", False)],
          sub="Value carries meaning, hue does not: one warm buff family, +22% R / -28% B off neutral.")
    strip(HERE / "h1_04_palette-deep.png", "DEEP  -  machine ground, where the industry looks competent",
          [("wet rock", WET_ABOVE, "deeper is wetter: depth is where the specular is", True),
           ("rock x (1-0.55)", tuple(c * 0.45 for c in DRY_LIT), "the same rock at full depth, darkened by the BFS field", True),
           ("cast iron, wet", CAST_IRON, "a century in: near-black, ferrous, matte, scaled", True),
           ("bearing steel", BEARING, "still working: slew ring, hammer face, winch face", True),
           ("winch 1900 K", kelvin(1900), "click 1 of nine", True),
           ("winch 2400 K", kelvin(2400), "click 9: the countdown is a colour ramp", True),
           ("strike 4000 K", kelvin(4000), "one frame; the only white light in the game", True),
           ("KILL (overlay)", KILL, "the winch must stay clearly short of this", False)],
          sub="Kelvin swatches from a Planckian-locus fit, normalised; the Blender rule is a Blackbody node, not these RGBs.")
    strip(HERE / "h1_05_palette-water.png", "WATER  -  the flooding axis, never a blue tint",
          [("tide-mark crust", TIDE, "0.12 m above the line, albedo x1.7, matte: the water moved", True),
           ("wet, above", WET_ABOVE, "", True),
           ("submerged", SUBMERGED, "below the line: albedo x0.6, roughness 0.10", True),
           ("WATER (display)", WATER, "cool because water is cool, not because flooding is a colour", False),
           ("underwater medium", UNDERWATER, "scatter 0.35, absorption off red, anisotropy 0.8; light dies in 4-6 m", True),
           ("graphitised iron", GRAPHITISED, "cast iron under water: intact in silhouette, dead in surface", True),
           ("corona 2100 K", kelvin(2100), "the Bus, live: the water glows, the conductor never does (guess: ~0.02 linear)", True)])
    strip(HERE / "h1_06_palette-works.png", "THE WORKS  -  everything ruined except what is still in use",
          [("cast iron", CAST_IRON, "every casting: fillets, ribs, draft, a foundry mark, no dates", True),
           ("graphitised", GRAPHITISED, "below the waterline", True),
           ("porcelain", PORCELAIN, "the Bus's insulators: the only clean white in the game", True),
           ("polished rail", BEARING, "rail heads mirror-bright by use: the one long shot the cave allows", True),
           ("grease, wet", (0.03, 0.025, 0.018), "the Haulage's bearings (guess)", True),
           ("timber, wet", (0.10, 0.07, 0.045), "sets, sleepers, hoarding on the surface (guess)", True),
           ("residual 2100 K", RESIDUAL, "the contingency circuit: boxed, needs a ruling", True)])
    strip(HERE / "h1_07_palette-belief-and-accents.png", "BELIEF, AND THE ACCENTS  -  overlay vocabulary only, shown once",
          [("SENSED", SENSED, "a point the sensor returned; confidence is alpha", False),
           ("WALKED", WALKED, "ground it only passed through", False),
           ("GHOST", GHOST, "believed pose, its ellipse, every hollow mark", False),
           ("COOL_DIM", COOL_DIM, "believed trail, the chain", False),
           ("HAZARD", HAZARD, "the machinery's field, never its body", False),
           ("LIE", LIE, "a fix that moved the world; the spoof", False),
           ("CARGO", CARGO, "the objective; the actions a stop offers", False),
           ("KILL", KILL, "lethal and nothing else", False),
           ("HURT", HURT, "hurt and alive; not a second red", False)],
          sub="palette.py's twenty-four, the half that is never paint. Cyan is belief: nothing in the world may be cyan.")
    # what is never a colour
    w, h = 1400, 330
    im = Image.new("RGB", (w, h), to8(VOID))
    d = ImageDraw.Draw(im)
    d.text((20, 14), "WHAT IS NEVER A COLOUR  -  ART-DIRECTION 9", fill=to8(PRIMARY), font=font(26))
    rules = [("cyan in the world", (0.2, 0.9, 1.0), "the model's default light; every renderer must retint it"),
             ("a second red", (0.9, 0.2, 0.2), "SKINS['salvage'].light; red warning strips; red-hot iron"),
             ("biome hue", (0.35, 0.55, 0.30), "rock type, magnetic character, depth: surface only, never hue"),
             ("glowing ore", (0.3, 0.9, 0.5), "no crystal, no ice, no bioluminescence"),
             ("orange rust", (0.75, 0.35, 0.08), "dry rust; this iron has been under water"),
             ("a sun", (1.0, 0.95, 0.8), "the cave has no sun and may never borrow one; the surface sky is overcast (guess)"),
             ("blue for flooding", (0.15, 0.3, 0.7), "WATER is cool because water is; flooding is a waterline")]
    sw = (w - 40) // len(rules)
    for i, (name, rgb, why) in enumerate(rules):
        x = 20 + i * sw
        d.rectangle((x, 80, x + sw - 6, 210), fill=to8(rgb), outline=to8(RULE))
        d.line((x, 80, x + sw - 6, 210), fill=to8(KILL), width=6)
        d.line((x + sw - 6, 80, x, 210), fill=to8(KILL), width=6)
        d.text((x + 6, 220), name, fill=to8(PRIMARY), font=font(17))
        words, lines, cur = why.split(), [], ""
        for wd in words:
            if d.textlength(cur + " " + wd, font=font(13)) > sw - 14:
                lines.append(cur)
                cur = wd
            else:
                cur = (cur + " " + wd).strip()
        lines.append(cur)
        for k, ln in enumerate(lines[:5]):
            d.text((x + 6, 244 + k * 16), ln, fill=to8(TERTIARY), font=font(13))
    im.save(HERE / "h1_08_palette-never.png")
    print("wrote h1_08")


def light_sources():
    """Rows = zones; each source a swatch at its colour, a bar for its reach, a note. Plus the exposure contract."""
    rows = [
        ("SURFACE", [("overcast sky", SKY12000, None, "everything, from above; no sun, no shadow edge (guess)"),
                     ("terminal screen, night", (0.55, 0.62, 0.72), 1.5, "the surface's one emissive; lights a bench and a face (guess)"),
                     ("pendant screen", (0.55, 0.62, 0.72), 0.5, "lights the hands that hold it (guess)")]),
        ("SHAFT", [("daylight 12000 K", SKY12000, 8.0, "its own chamber, a disc from below")]),
        ("SHALLOW", [("work lamp", LAMP, 6.0, "floor to ~6 m, walls to ~20 m; 50 deg, 8-10 deg down"),
                     ("running lights", BONE, 1.5, "retroreflective: return a lamp that hits them (decision #1)"),
                     ("beacon pilot", WARM_DIM, 3.6, "useful to 3.6 m, seen to ~20 m")]),
        ("DEEP", [("winch head 1900-2400 K", kelvin(2100), 18.0, "a beacon from the next chamber; nine 1 s clicks"),
                  ("anvil 1900-2400 K", kelvin(2100), 6.0, "a third the output; lights the floor the agents stand on"),
                  ("strike 4000 K", kelvin(4000), 18.0, "one frame at ~4x; the only white light"),
                  ("residual 2100 K (boxed)", RESIDUAL, 5.0, "contingency; ship only on a ruling")]),
        ("WATER", [("lamp, underwater", LAMP, 5.0, "dies in 4-6 m; scatter 0.35"),
                   ("Bus corona 2100 K", kelvin(2100), 2.0, "the water under a live conductor (guess: ~0.02 linear)")]),
        ("THE WORKS", [("Haulage lamp", LAMP, 6.0, "the only moving light besides agents (guess that it carries one)"),
                       ("rail specular", BEARING, 20.0, "not a source: a mirror that returns your own lamp along its length")]),
    ]
    w = 1500
    rh = 40
    n = sum(len(r[1]) for r in rows)
    h = 120 + n * rh + len(rows) * 26 + 190
    im = Image.new("RGB", (w, h), to8(VOID))
    d = ImageDraw.Draw(im)
    d.text((20, 14), "THE LIGHT SOURCES THAT EXIST, BY ZONE  -  ART-DIRECTION 2.1", fill=to8(PRIMARY), font=font(26))
    d.text((20, 48), "swatch = colour; bar = reach in metres on a 20 m scale; 'seen' is further than 'lit' for every point source", fill=to8(SECONDARY), font=font(15))
    bx0, bx1 = 560, 1060
    for k in range(0, 21, 5):
        x = bx0 + (bx1 - bx0) * k / 20
        d.line((x, 80, x, 88), fill=to8(TERTIARY))
        d.text((x - 8, 90), f"{k} m", fill=to8(TERTIARY), font=font(12))
    y = 112
    for zone, srcs in rows:
        d.text((20, y), zone, fill=to8(SECONDARY), font=font(16))
        y += 24
        for name, rgb, reach, note in srcs:
            disp = tuple(lin2srgb(c) for c in rgb) if max(rgb) <= 1.0 and zone != "" else rgb
            d.rectangle((40, y + 4, 90, y + rh - 8), fill=to8(disp), outline=to8(RULE))
            d.text((100, y + 8), name, fill=to8(PRIMARY), font=font(16))
            if reach is None:
                d.rectangle((bx0, y + 12, bx1, y + rh - 16), fill=to8(disp))
            else:
                d.rectangle((bx0, y + 12, bx0 + (bx1 - bx0) * min(reach, 20) / 20, y + rh - 16), fill=to8(disp))
            d.text((bx1 + 16, y + 10), note, fill=to8(TERTIARY), font=font(13))
            y += rh
        y += 2
    y += 12
    d.line((20, y, w - 20, y), fill=to8(RULE))
    y += 12
    d.text((20, y), "THE EXPOSURE CONTRACT (linearised, per lamp frame)", fill=to8(SECONDARY), font=font(16))
    y += 26
    bands = [("> 0.50 blown", "<= 3%", (0.9, 0.9, 0.9)), ("> 0.18 mid", "1-25%", (0.5, 0.5, 0.5)),
             ("> 0.05 legible", "3-20%", (0.22, 0.22, 0.22)), ("< 0.02 true black", ">= 70%", (0.02, 0.02, 0.02))]
    x = 40
    for name, share, val in bands:
        d.rectangle((x, y, x + 300, y + 60), fill=to8(tuple(lin2srgb(c) for c in val)), outline=to8(RULE))
        d.text((x + 8, y + 6), name, fill=to8(PRIMARY) if val[0] < 0.4 else to8(VOID), font=font(16))
        d.text((x + 8, y + 32), share + " of frame", fill=to8(SECONDARY) if val[0] < 0.4 else to8(PANEL), font=font(14))
        x += 320
    y += 72
    d.text((40, y), "The surface has no contract yet: DAYLIGHT frames run 40-70% legible and the CLEAR rig is a catalogue rig. Both are guesses.", fill=to8(TERTIARY), font=font(13))
    im.save(HERE / "h2_01_light-sources.png")
    print("wrote h2_01")
    # the 75 s cycle as a strip
    w, h = 1500, 300
    im = Image.new("RGB", (w, h), to8(VOID))
    d = ImageDraw.Draw(im)
    d.text((20, 14), "THE ASSAYER'S 75 s AS LIGHT  -  THE-MACHINERY 3, ART-DIRECTION 5.4", fill=to8(PRIMARY), font=font(26))
    x0, x1, yb = 40, 1460, 110
    for s in range(0, 76, 5):
        x = x0 + (x1 - x0) * s / 75
        d.line((x, yb + 70, x, yb + 78), fill=to8(TERTIARY))
        d.text((x - 8, yb + 82), f"{s}", fill=to8(TERTIARY), font=font(12))
    d.rectangle((x0, yb, x0 + (x1 - x0) * 54 / 75, yb + 66), fill=to8((0.01, 0.01, 0.012)))
    d.text((x0 + 8, yb + 8), "0-54 dormant: nothing. one drip every two seconds onto the anvil", fill=to8(SECONDARY), font=font(14))
    xs = x0 + (x1 - x0) * 54 / 75
    d.rectangle((xs, yb, x0 + (x1 - x0) * 62 / 75, yb + 66), fill=to8((0.02, 0.02, 0.022)))
    d.text((xs + 4, yb + 8), "54-62 slew, lock:", fill=to8(SECONDARY), font=font(12))
    d.text((xs + 4, yb + 26), "bearing steel catches", fill=to8(SECONDARY), font=font(12))
    d.text((xs + 4, yb + 42), "whatever is present", fill=to8(SECONDARY), font=font(12))
    for k in range(9):
        T = 1900 + (2400 - 1900) * k / 8
        v = 0.15 + 0.85 * (k + 1) / 9
        rgb = tuple(lin2srgb(c * v) for c in kelvin(T))
        xa = x0 + (x1 - x0) * (62 + k) / 75
        xb = x0 + (x1 - x0) * (63 + k) / 75
        d.rectangle((xa, yb, xb - 1, yb + 66), fill=to8(rgb))
    d.text((x0 + (x1 - x0) * 50 / 75, yb - 24), "62-71 the wind: nine clicks, 1900 -> 2400 K, the tank down a ninth per click", fill=to8(SECONDARY), font=font(13))
    xf = x0 + (x1 - x0) * 71 / 75
    d.rectangle((xf, yb, xf + 4, yb + 66), fill=to8(kelvin_srgb(4000)))
    for k in range(40):
        t = k / 40
        v = (1 - t) ** 2 * 0.8
        rgb = tuple(lin2srgb(c * v) for c in kelvin(2000))
        xa = xf + 4 + (x1 - xf - 4) * k / 40
        xb = xf + 4 + (x1 - xf - 4) * (k + 1) / 40
        d.rectangle((xa, yb, xb, yb + 66), fill=to8(rgb))
    d.text((x0 + (x1 - x0) * 42 / 75, yb + 104), "71.0-71.15 the fire: one frame at ~4x, 4000 K.  then lethal 4 s, decay over 8 s as the brake cools", fill=to8(SECONDARY), font=font(13))
    d.text((40, 240), "Two hot points, not one: the winch head is a beacon (visible from the next chamber, lights no floor); the anvil at a third the output lights the ground the agents stand on.", fill=to8(TERTIARY), font=font(13))
    d.text((40, 260), "The winch emitting at all is a guess THE-MACHINERY never makes. Kelvin swatches are a locus fit; the Blender rule is a Blackbody node.", fill=to8(TERTIARY), font=font(13))
    im.save(HERE / "h2_02_assayer-cycle.png")
    print("wrote h2_02")


# ---- screens ----------------------------------------------------------------------------------
def pendant_mock(snaps):
    """The pendant's screen: the belief picture from the corridor (phase2 --snap), the predicates,
    the actions as numbered keys, and a legend for the five physical keys along the bottom edge."""
    W, H = 1200, 600
    im = Image.new("RGB", (W, H), to8(VOID))
    d = ImageDraw.Draw(im)
    src = Image.open(snaps / "p2-run3-stop.png").convert("RGB")
    # the canvas region of the window, cropped around the ghost
    crop = src.crop((470, 200, 1330, 860))
    crop.thumbnail((790, 540))
    im.paste(crop, (10, 22))
    d.rectangle((10, 22, 10 + crop.width, 22 + crop.height), outline=to8(RULE))
    d.text((18, 26), "ITS MAP", fill=to8(SECONDARY), font=font(15))
    d.text((18, 44), "what it thinks is there - and all you get to see", fill=to8(TERTIARY), font=font(12))
    x = 820
    d.text((x, 26), "STOPPED WHILE IT ASKS", fill=to8(SECONDARY), font=font(15))
    d.text((x, 46), "stop 4     1:12", fill=to8(PRIMARY), font=font(26))
    d.text((x, 96), "WHAT IT BELIEVES HERE", fill=to8(SECONDARY), font=font(15))
    d.text((x, 118), "a branch here that leads to", fill=to8(PRIMARY), font=font(17))
    d.text((x, 138), "unexplored ground", fill=to8(PRIMARY), font=font(17))
    d.text((x + 16, 160), "yes", fill=to8(CARGO), font=font(20))
    d.text((x, 192), "lost", fill=to8(PRIMARY), font=font(17))
    d.text((x + 16, 210), "theta = 64, provisional", fill=to8(TERTIARY), font=font(12))
    d.text((x + 16, 226), "no        16.3", fill=to8(PRIMARY), font=font(20))
    d.text((x, 262), "carrying", fill=to8(PRIMARY), font=font(17))
    d.text((x + 16, 282), "no", fill=to8(PRIMARY), font=font(20))
    d.text((x, 330), "WHAT YOU CAN DO", fill=to8(SECONDARY), font=font(15))
    d.text((x, 352), "[1]  take a branch", fill=to8(CARGO), font=font(20))
    d.text((x, 380), "[2]  go back", fill=to8(CARGO), font=font(20))
    d.text((x, 430), "THE RULE SO FAR", fill=to8(SECONDARY), font=font(15))
    for k, ln in enumerate(["If carrying, go back.", "Otherwise if a branch here leads", "to unexplored ground, take it.", "Otherwise go back."]):
        d.text((x, 450 + k * 18), ln, fill=to8(TERTIARY), font=font(14))
    # the key legend along the bottom edge: one label per physical key under the screen
    d.line((0, 560, W, 560), fill=to8(RULE))
    for k, lab in enumerate(["1  branch", "2  back", "3  -", "4  -", "5  -"]):
        d.text((50 + k * 190, 570), lab, fill=to8(CARGO) if k < 2 else to8(TERTIARY), font=font(18))
    d.text((W - 190, 574), "wheel: scrub", fill=to8(TERTIARY), font=font(14))
    im.save(HERE / "g2_02_pendant-screen-mock.png")
    print("wrote g2_02")


def terminal_mock(snaps):
    """The bench terminal shows phase2's window after induction: the map of every demonstration, the
    rule as a tree and as one sentence. Reused as-is at the terminal's aspect, with a replay scrubber."""
    src = Image.open(snaps / "p2-tree.png").convert("RGB")
    W, H = 1600, 1000
    im = Image.new("RGB", (W, H), to8(VOID))
    s = src.copy()
    s.thumbnail((W, 940))
    im.paste(s, (0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 940, W, H), fill=to8(PANEL))
    d.line((40, 972, W - 40, 972), fill=to8(RULE), width=3)
    d.line((40, 972, 40 + (W - 80) * 0.83, 972), fill=to8(COOL_DIM), width=3)
    px = 40 + (W - 80) * 0.83
    d.polygon([(px - 7, 958), (px + 7, 958), (px, 972)], fill=to8(LIE))
    d.text((40, 946), "REPLAY  demonstration 3, stop 61 of 62   -   scrub with the wheel, take over with a key, promote", fill=to8(SECONDARY), font=font(14))
    im.save(HERE / "g2_06_terminal-screen-mock.png")
    print("wrote g2_06")
    # the replay for the night shot: the 8:00 reveal, both layers, with the same scrubber
    src = Image.open(snaps / "p1spec" / "snap_480.png").convert("RGB")
    im = Image.new("RGB", (W, H), to8(VOID))
    s = src.copy()
    s.thumbnail((W, 940))
    im.paste(s, (0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 940, W, H), fill=to8(PANEL))
    d.line((40, 972, W - 40, 972), fill=to8(RULE), width=3)
    d.line((40, 972, W - 40, 972), fill=to8(COOL_DIM), width=3)
    d.polygon([(W - 47, 958), (W - 33, 958), (W - 40, 972)], fill=to8(LIE))
    d.text((40, 946), "REPLAY  8:00 of 8:00   -   truth over belief: what was actually there, and what it thought", fill=to8(SECONDARY), font=font(14))
    (HERE / "_screens").mkdir(exist_ok=True)
    im.save(HERE / "_screens" / "terminal_replay.png")
    im.save(HERE / "g5_01_terminal-replay-mock.png")
    print("wrote _screens/terminal_replay, g5_01")
    # the listening post: belief only, the cave's ITS MAP, during the run
    src = Image.open(snaps / "p1teach" / "teach_stop2.png").convert("RGB")
    post = src.crop((0, 60, 1620, 1000))
    post.thumbnail((1400, 810))
    post.save(HERE / "_screens" / "post_belief.png")
    src.save(HERE / "_screens" / "pendant_cave.png")
    print("wrote _screens/post_belief, pendant_cave")


def course_plan(seed):
    """Truth plan of Corridor(seed) at 0.6 m/cell, as the course would be built on the spoil flat."""
    from phase2.truth.corridor import Corridor
    C = Corridor(seed)
    pos = {i: (x * 0.6, y * 0.6) for i, (x, y) in C.layout().items()}
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    W, H = 1400, 900
    pad = 70
    sx = (W - 2 * pad) / max(max(xs) - min(xs), 1)
    sy = (H - 2 * pad - 60) / max(max(ys) - min(ys), 1)
    sc = min(sx, sy)

    def P(i):
        x, y = pos[i]
        return (pad + (x - min(xs)) * sc, H - pad - (y - min(ys)) * sc)

    im = Image.new("RGB", (W, H), to8(VOID))
    d = ImageDraw.Draw(im)
    for pid, p in C.passages.items():
        a, b = P(p.near), P(p.far)
        d.line((a, b), fill=to8(WARM_DIM), width=max(2, int(1.8 * sc)))
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        d.text((mx + 4, my - 8), f"{p.length * 0.6:.0f} m", fill=to8(TERTIARY), font=font(11))
    for i, n in C.nodes.items():
        x, y = P(i)
        r = 5
        if i == C.shaft:
            d.ellipse((x - 9, y - 9, x + 9, y + 9), outline=to8(BONE), width=2)
            d.text((x + 12, y - 8), "root post (the 'shaft' beacon)", fill=to8(BONE), font=font(13))
        elif i == C.deposit:
            d.rectangle((x - 7, y - 7, x + 7, y + 7), outline=to8(CARGO), width=2)
            d.text((x + 12, y - 8), "the cargo crate", fill=to8(CARGO), font=font(13))
        elif n.onward:
            d.ellipse((x - r, y - r, x + r, y + r), fill=to8(WARM_DIM))
            d.text((x + 8, y - 16), f"J{i}", fill=to8(SECONDARY), font=font(12))
        else:
            d.line((x - 5, y - 5, x + 5, y + 5), fill=to8(TERTIARY), width=2)
            d.line((x - 5, y + 5, x + 5, y - 5), fill=to8(TERTIARY), width=2)
    # passages that cross: the graph is not embedded in the plane, which a physical course cannot ignore
    def seg_x(p, q):
        (a, b), (c, e) = (P(p.near), P(p.far)), (P(q.near), P(q.far))
        def ccw(u, v, w):
            return (w[1] - u[1]) * (v[0] - u[0]) > (v[1] - u[1]) * (w[0] - u[0])
        if len({p.near, p.far, q.near, q.far}) < 4:
            return None
        if ccw(a, c, e) != ccw(b, c, e) and ccw(a, b, c) != ccw(a, b, e):
            d1 = (b[0] - a[0], b[1] - a[1]); d2 = (e[0] - c[0], e[1] - c[1])
            den = d1[0] * d2[1] - d1[1] * d2[0]
            t = ((c[0] - a[0]) * d2[1] - (c[1] - a[1]) * d2[0]) / den
            return (a[0] + d1[0] * t, a[1] + d1[1] * t)
        return None
    crossings = []
    ps = list(C.passages.values())
    for i in range(len(ps)):
        for j in range(i + 1, len(ps)):
            pt = seg_x(ps[i], ps[j])
            if pt:
                crossings.append(pt)
    for (x, y) in crossings:
        d.ellipse((x - 11, y - 11, x + 11, y + 11), outline=to8(KILL), width=2)
    if crossings:
        d.text((20, H - 40), f"{len(crossings)} crossings (red): the graph is not planar; a physical course needs a layout pass (NOTES, design problem 2)", fill=to8(KILL), font=font(13))
    first = C.nodes[C.passages[0].far]
    x, y = P(first.id)
    d.ellipse((x - 16, y - 16, x + 16, y + 16), outline=to8(LIE), width=2)
    d.text((x + 20, y + 6), "the junction the board stages (g1_02)", fill=to8(LIE), font=font(13))
    d.text((20, 14), f"THE COURSE, IN PLAN  -  phase2 Corridor(seed {seed}) at 0.6 m/cell", fill=to8(PRIMARY), font=font(24))
    d.text((20, 44), "truth. walls 1.2 m high, passages 1.8 m wide (guess); 8 junctions of 2-3 onward passages; leaves dead-end; one crate.", fill=to8(SECONDARY), font=font(14))
    ext = f"extent {max(xs) - min(xs):.0f} x {max(ys) - min(ys):.0f} m; passages {min(p.length for p in C.passages.values()) * 0.6:.0f}-{max(p.length for p in C.passages.values()) * 0.6:.0f} m"
    d.text((20, 64), ext + "   (phase2/tuning.py says 1 cell ~ 1 m; the art uses 0.6: see NOTES)", fill=to8(TERTIARY), font=font(13))
    bx = W - pad - 10 * sc
    d.line((bx, H - 30, bx + 10 * sc, H - 30), fill=to8(PRIMARY), width=3)
    d.text((bx, H - 52), "10 m", fill=to8(PRIMARY), font=font(13))
    im.save(HERE / "g1_07_course-plan.png")
    print("wrote g1_07", ext, "crossings", len(crossings))


# ---- post: contact sheets from the renders ------------------------------------------------------
def load(name):
    p = HERE / name
    return Image.open(p).convert("RGB") if p.exists() else None


def caption_sheet(path, title, panels, cols=3, cell=(460, 300), sub=None):
    rows = math.ceil(len(panels) / cols)
    W = 20 + cols * (cell[0] + 16)
    H = 90 + rows * (cell[1] + 70)
    im = Image.new("RGB", (W, H), to8(VOID))
    d = ImageDraw.Draw(im)
    d.text((20, 14), title, fill=to8(PRIMARY), font=font(24))
    if sub:
        d.text((20, 46), sub, fill=to8(SECONDARY), font=font(14))
    for k, (name, cap) in enumerate(panels):
        r, c = divmod(k, cols)
        x = 20 + c * (cell[0] + 16)
        y = 80 + r * (cell[1] + 70)
        img = load(name)
        if img is None:
            d.rectangle((x, y, x + cell[0], y + cell[1]), outline=to8(RULE))
            d.text((x + 10, y + 10), f"missing: {name}", fill=to8(KILL), font=font(13))
        else:
            im2 = img.copy()
            im2.thumbnail(cell)
            im.paste(im2, (x, y))
        d.text((x, y + cell[1] + 6), f"{k + 1}.  {cap}", fill=to8(SECONDARY), font=font(14))
        d.text((x, y + cell[1] + 26), name, fill=to8(TERTIARY), font=font(11, mono=True))
    im.save(path)
    print("wrote", path)


def two_panel(path, left, right, title, lcap, rcap, w=960):
    a, b = load(left), load(right)
    if b is None:
        b = Image.open(right).convert("RGB") if Path(right).exists() else None
    if a is None or b is None:
        print("skip", path, a is None, b is None)
        return
    ah = int(a.height * w / a.width)
    bh = int(b.height * w / b.width)
    h = max(ah, bh)
    a = a.resize((w, ah))
    b = b.resize((w, bh))
    im = Image.new("RGB", (2 * w + 30, h + 100), to8(VOID))
    im.paste(a, (10, 60))
    im.paste(b, (w + 20, 60))
    d = ImageDraw.Draw(im)
    d.text((10, 12), title, fill=to8(PRIMARY), font=font(24))
    d.text((10, h + 66), lcap, fill=to8(SECONDARY), font=font(15))
    d.text((w + 20, h + 66), rcap, fill=to8(SECONDARY), font=font(15))
    im.save(path)
    print("wrote", path)


def tone_rows():
    """One tone row per zone, sampled from the finished in-situ frames: sixteen bins of the frame's
    luminance histogram, drawn as the mean colour of each bin. What the frames actually contain."""
    frames = [("surface, overcast", "g1_02_junction-over-the-shoulder.png"), ("surface, drizzle", "g1_05_junction-drizzle.png"),
              ("surface, dusk", "g2_05_terminal-dusk.png"), ("surface, night", "g5_02_leanto-night.png"),
              ("the collar, commit", "g3_03_commit-wide.png"), ("the cave stop", "g4_01_cave-stop-truth.png")]
    W, rh = 1400, 70
    im = Image.new("RGB", (W, 80 + rh * len(frames) + 40), to8(VOID))
    d = ImageDraw.Draw(im)
    d.text((20, 14), "TONE ROWS  -  sampled from the board's in-situ renders", fill=to8(PRIMARY), font=font(24))
    d.text((20, 46), "each row: the frame's pixels sorted by luminance into 16 bins, each bin painted its mean colour, bin width = its share of the frame", fill=to8(SECONDARY), font=font(13))
    y = 80
    for name, fn in frames:
        img = load(fn)
        d.text((20, y + 22), name, fill=to8(PRIMARY), font=font(15))
        if img is None:
            d.text((300, y + 22), f"missing {fn}", fill=to8(KILL), font=font(13))
            y += rh
            continue
        sm = img.resize((160, 100))
        px = list(sm.getdata())
        px.sort(key=lambda p: 0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2])
        n = len(px)
        x = 300
        for k in range(16):
            chunk = px[k * n // 16:(k + 1) * n // 16]
            mean = tuple(sum(c[i] for c in chunk) // len(chunk) for i in range(3))
            d.rectangle((x, y + 8, x + 68, y + rh - 8), fill=mean)
            x += 68
        blk = sum(1 for p in px if (0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]) < 36) / n   # sRGB 36 ~ linear 0.02
        d.text((x + 12, y + 22), f"{blk * 100:.0f}% under linear 0.02", fill=to8(TERTIARY), font=font(13))
        y += rh
    im.save(HERE / "h1_09_tone-rows.png")
    print("wrote h1_09")


def assayer_cycle():
    """h2_02: the 75-second cycle as light. ART-DIRECTION 5.4 / THE-MACHINERY 3: 54 s of nothing, the
    slew (nothing; the bearing catches whatever is present), locked, nine 1 s clicks ramping 0 -> full
    at 1900 -> 2400 K, one 0.15 s frame at ~4x at 4000 K, then decay over 8 s. Two hot points: the
    winch head (a beacon, seen from the next chamber) and the anvil at a third the output (lights the
    floor the agents stand on). Kelvin swatches are the Planckian fit; the Blender rule is a Blackbody node."""
    W, H = 1500, 560
    im = Image.new("RGB", (W, H), to8(VOID))
    d = ImageDraw.Draw(im)
    d.text((20, 14), "THE ASSAYER'S 75 SECONDS AS LIGHT  -  ART-DIRECTION 5.4, THE-MACHINERY 3", fill=to8(PRIMARY), font=font(24))
    d.text((20, 46), "two sources, the winch head (beacon) and the anvil (a third: the floor). Output is relative to the wind's full; the strike is ~4x for one frame.",
           fill=to8(SECONDARY), font=font(13))
    x0, x1, yb, yt = 90, W - 40, 330, 110         # the graph: seconds along x, output up y
    sx = (x1 - x0) / 75.0
    # phases, as bands
    bands = [(0, 54, "listening: nothing", TERTIARY), (54, 57, "slew", TERTIARY), (57, 62, "locked", TERTIARY),
             (62, 71, "the wind: nine clicks", LIE), (71, 75, "lethal", KILL)]
    for a, b, lab, colr in bands:
        d.rectangle((x0 + a * sx, yt - 8, x0 + b * sx, yb), outline=to8(RULE))
        yy = yb + 6 if a != 57 else yb + 40          # the 3 s and 5 s bands are too narrow for two labels side by side
        d.text((x0 + a * sx + 6, yy), f"{a}-{b} s", fill=to8(colr), font=font(12))
        d.text((x0 + a * sx + 6, yy + 16), lab, fill=to8(colr), font=font(12))
    # output curve, winch head (full) and anvil (third), drawn as bars per second with the colour at that Kelvin
    def out_at(t):
        if t < 62:
            return 0.0, None
        if t < 71:
            k = int(t - 62) + 1                  # click 1..9
            T = 1900 + (2400 - 1900) * (k - 1) / 8
            return k / 9.0, T
        if t < 71.15:
            return 4.0, 4000
        return math.exp(-(t - 71.15) / 3.5), 2400   # "decay over 8 s as the brake cools" (guess: e-fold 3.5 s)
    scale = (yb - yt) / 1.0                          # full wind = the graph height; the strike clips
    step = 0.25
    t = 0.0
    while t < 75:
        o, T = out_at(t)
        if o > 0:
            colr = to8(kelvin_srgb(T)) if T else to8(PRIMARY)
            h = min(o, 1.0) * scale
            d.rectangle((x0 + t * sx, yb - h, x0 + (t + step) * sx, yb), fill=colr)
            ha = min(o / 3.0, 1.0) * scale
            d.rectangle((x0 + t * sx, yb - ha, x0 + (t + step) * sx, yb), outline=to8(PANEL))
        t += step
    # the strike as a marker above the graph (it would be 4x the height)
    xs_ = x0 + 71.05 * sx
    d.polygon([(xs_ - 9, yt - 30), (xs_ + 9, yt - 30), (xs_, yt - 10)], fill=to8(kelvin_srgb(4000)))
    d.text((xs_ - 60, yt - 50), "71.00-71.15 s: 4000 K, ~4x", fill=to8(PRIMARY), font=font(12))
    d.text((x0 - 70, yt - 8), "full", fill=to8(TERTIARY), font=font(12))
    d.text((x0 - 70, yb - 8), "0", fill=to8(TERTIARY), font=font(12))
    d.text((x0 - 70, yb - scale / 3 - 8), "anvil", fill=to8(TERTIARY), font=font(11))
    d.line((x0, yb - scale / 3, x1, yb - scale / 3), fill=to8(RULE))
    # the nine clicks as swatches with their Kelvin
    y = 400
    d.text((20, y - 24), "the nine clicks, 1 s each: colour at each step (winch head; the anvil is the same colour at a third)", fill=to8(SECONDARY), font=font(13))
    for k in range(9):
        T = 1900 + 500 * k / 8
        xk = 20 + k * 120
        c = kelvin_srgb(T)
        lvl = (k + 1) / 9.0
        d.rectangle((xk, y, xk + 104, y + 70), fill=tuple(int(v * lvl) for v in to8(c)))
        d.text((xk, y + 76), f"click {k + 1}", fill=to8(PRIMARY), font=font(12))
        d.text((xk, y + 92), f"{int(T)} K  {lvl:.2f}", fill=to8(TERTIARY), font=font(11, mono=True))
    xk = 20 + 9 * 120 + 30
    d.rectangle((xk, y, xk + 104, y + 70), fill=to8(kelvin_srgb(4000)))
    d.text((xk, y + 76), "the fire", fill=to8(PRIMARY), font=font(12))
    d.text((xk, y + 92), "4000 K  4.0", fill=to8(TERTIARY), font=font(11, mono=True))
    xk += 140
    d.rectangle((xk, y, xk + 104, y + 70), fill=to8(KILL))
    d.text((xk, y + 76), "KILL #FF3B30", fill=to8(PRIMARY), font=font(12))
    d.text((xk, y + 92), "overlay only; 1900 K stays short of it", fill=to8(TERTIARY), font=font(10))
    d.text((20, H - 40), "Guesses: that the winch emits at all (THE-MACHINERY never says it glows); the anvil as a second source; the e-fold of the decay; the tank draw-down needs a sight-glass to be visible.",
           fill=to8(TERTIARY), font=font(12))
    im.save(HERE / "h2_02_assayer-cycle.png")
    print("wrote h2_02")


if A.stage == "pre":
    snaps = Path(A.snaps)
    pendant_mock(snaps)
    terminal_mock(snaps)
    course_plan(A.seed)
    palette_strips()
    light_sources()
elif A.stage == "post":
    snaps = Path(A.snaps) if A.snaps else None
    assayer_cycle()
    two_panel(HERE / "g4_04_cave-stop-exposure-pair.png", "g4_01_cave-stop-truth.png", "g4_05_cave-stop-plus3.png",
              "THE CAVE STOP  -  at the game's exposure, and at +3 stops so the board shows what is there",
              "in-situ: world background 0, the machine's own lamp, nothing else. This is the game.",
              "the SAME frame at +3 stops: the passage, the rubble, the mud on the legs. Not the game.")
    two_panel(HERE / "g4_02_stop-two-panel.png", "g4_01_cave-stop-truth.png", str(HERE / "_screens" / "pendant_cave.png"),
              "THE SAME STOP, TWICE  -  what the spectator could see, and what the player gets",
              "truth, rendered: the machine halted, head down, in its own lamp; the clock stopped",
              "belief, drawn: the pendant's picture of the same moment (python -m phase1 --teach --snap)")
    two_panel(HERE / "g0_02_surface-vs-cave.png", "g1_02_junction-over-the-shoulder.png", "g4_01_cave-stop-truth.png",
              "ONE ACT, TWO PLACES  -  the stop on the course and the stop in the cave",
              "the course: full information, a person over the wall, a wire",
              "the cave: the same stop through the link; the pendant shows the same belief-only picture")
    caption_sheet(HERE / "g0_01_teaching-loop-storyboard.png", "THE TEACHING LOOP AS A PLACE  -  six frames in order",
                  [("g1_02_junction-over-the-shoulder.png", "teach it at the course: it stops, you answer on the pendant"),
                   ("g2_05_terminal-dusk.png", "compose and read the rule at the bench terminal"),
                   ("g2_04_pendant-at-collar.png", "plug in at the collar: the last check before it goes"),
                   ("g3_03_commit-wide.png", "commit: the cable is out, the kibble is down, the shaft is black"),
                   ("g4_01_cave-stop-truth.png", "it stops underground; the same question comes up the link"),
                   ("g5_02_leanto-night.png", "the replay on the bench, at night: both layers, the one lit screen")],
                  sub="Everything in this row is a proposal (NOTES.md Q1-Q5). The pictures exist so the proposal can be refused precisely.")
    caption_sheet(HERE / "h2_03_sources-contact.png", "ONE IN-SITU FRAME PER SOURCE  -  from this board's renders",
                  [("g1_02_junction-over-the-shoulder.png", "the overcast sky, from above, no shadow edge"),
                   ("g3_04_descent-from-collar.png", "the sky as the shaft's disc, lighting the kibble from above"),
                   ("g5_02_leanto-night.png", "the terminal screen: the surface's one emissive"),
                   ("g1_08_roofed-section.png", "the work lamp, on the surface, under a roof (proposal)"),
                   ("g4_01_cave-stop-truth.png", "the work lamp, in the cave: the pool, the near wall, the black"),
                   ("g1_05_junction-drizzle.png", "the pendant screen in drizzle: lights the hands, nothing else")])
    tone_rows()
