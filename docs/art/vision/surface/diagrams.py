"""PIL diagrams for the surface board: no Blender. Run with the repo's .venv python from the repo root:

  .venv/Scripts/python.exe docs/art/vision/surface/diagrams.py [--snaps DIR] [--composites]

Writes 00_*.png beside this file. --composites (after the renders land) also writes the descent
strip, the sky strip of renders, and the teach-wide ghost overlay from the projection JSON the
render wrote.
"""
import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

PAPER = (233, 228, 218)
INK = (27, 26, 24)
INK2 = (110, 104, 96)
IRON = (60, 40, 30)
KIT = (168, 160, 145)
BONE = (242, 230, 210)
SENSED = (99, 214, 247)
WALKED = (46, 72, 84)
GHOST = (159, 232, 255)
WARM_DIM = (122, 102, 80)
VOID = (6, 8, 11)
SKY = (0.60, 0.74, 1.00)
CELL = 0.6


def font(size, mono=False):
    for cand in (["C:/Windows/Fonts/consola.ttf"] if mono else ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]):
        if os.path.exists(cand):
            return ImageFont.truetype(cand, size)
    return ImageFont.load_default()


def course_layout(seed=54, origin=(28.0, -6.0)):
    from phase2.truth.corridor import Corridor
    C = Corridor(seed)
    L = C.layout()
    xs = [v[0] for v in L.values()]; ys = [v[1] for v in L.values()]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    rot = -math.atan2(cy, cx)
    pos = {}
    for k, (x, y) in L.items():
        xr = x * math.cos(rot) - y * math.sin(rot)
        yr = x * math.sin(rot) + y * math.cos(rot)
        pos[k] = (origin[0] + xr * CELL, origin[1] + yr * CELL)
    return C, pos


# -------------------------------------------------------------------------------------------
def pithead_plan(path):
    """A1. Plan of the whole site at one scale, with the compound enlarged in an inset."""
    W, H = 1400, 900
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    f, fs, fm = font(20), font(15), font(14, True)
    # site: 4 px/m, x -50..180, y -80..90 ; y up
    s = 4.0
    ox, oy = 60 + 50 * s, 40 + 90 * s

    def P(x, y):
        return (ox + x * s, oy - y * s)
    d.text((60, 14), "THE PIT-HEAD, plan (proposal). 0.6 m/cell; the course is phase2 seed 54 at true scale", font=f, fill=INK)
    # hardstanding
    d.rectangle([P(-16, 18), P(16, -10)], outline=INK2, width=1)
    # course
    C, pos = course_layout()
    for p in C.passages.values():
        a, b = pos[p.near], pos[p.far]
        d.line([P(*a), P(*b)], fill=INK, width=int(1.8 * s))
        d.line([P(*a), P(*b)], fill=PAPER, width=max(1, int(1.8 * s) - 3))
    for k, (x, y) in pos.items():
        r = 3 if k not in (C.shaft, C.deposit) else 6
        d.ellipse([P(x - r / s, y + r / s), P(x + r / s, y - r / s)], fill=WARM_DIM if k == C.shaft else (KIT if k == C.deposit else INK))
    d.text(P(pos[C.shaft][0] - 4, pos[C.shaft][1] - 3), "root: the 'shaft' beacon", font=fs, fill=INK2)
    d.text(P(pos[C.deposit][0] + 1.5, pos[C.deposit][1] + 1.5), "cargo crate (the deposit leaf)", font=fs, fill=INK2)
    # compound symbols
    d.rectangle([P(-2.2, 2.0), P(2.2, -2.0)], fill=IRON)
    d.polygon([P(-2.7, -2.6), P(2.7, -2.6), P(2.5, 7.2), P(-2.5, 7.2)], outline=IRON, width=2)
    d.rectangle([P(-4.5, 20.5), P(4.5, 13.5)], outline=INK, width=2)
    d.rectangle([P(-11.5, 18.6), P(-4.5, 13.4)], outline=INK2, width=1)
    d.rectangle([P(-0.9, 10.2), P(0.9, 8.8)], fill=KIT)
    d.ellipse([P(-3.7, -2.3), P(-2.7, -3.3)], fill=KIT)
    for (x, y, sx, sy) in [(-34, -22, 14, 6), (-44, 10, 12, 7), (-28, 38, 16, 6), (16, 44, 18, 7), (-14, -44, 20, 8), (60, 78, 22, 8), (36, -62, 20, 8), (150, 20, 30, 10), (95, -70, 26, 9), (130, 100, 28, 10)]:
        d.ellipse([P(x - sx, y + sy), P(x + sx, y - sy)], outline=INK2, width=1)
    d.text(P(60, 82), "spoil heaps", font=fs, fill=INK2)
    d.text(P(-16, -12), "hardstanding 32 x 28 m", font=fs, fill=INK2)
    d.text(P(-4.5, 22.5), "winding house (dead)", font=fs, fill=INK)
    d.text(P(-24, 12), "yard lean-to", font=fs, fill=INK)
    d.text(P(3.5, 1), "collar + headframe", font=fs, fill=INK)
    d.text(P(2, 10), "winch", font=fs, fill=INK2)
    d.text(P(-12, -6), "listening post", font=fs, fill=INK2)
    # scale bar
    d.line([P(-40, -70), P(10, -70)], fill=INK, width=3)
    d.text(P(-40, -72), "50 m", font=fs, fill=INK)
    d.text(P(-45, 85), "N up. +X east.", font=fs, fill=INK2)
    # inset: the compound at 12 px/m
    ix, iy, iw, ih = W - 520, 70, 480, 440
    d.rectangle([ix, iy, ix + iw, iy + ih], fill=(224, 219, 208), outline=INK, width=2)
    s2 = 11.0
    ox2, oy2 = ix + 18 * s2, iy + 26 * s2

    def Q(x, y):
        return (ox2 + x * s2, oy2 - y * s2)
    d.text((ix + 10, iy + 8), "the compound, 1 px = 9 cm", font=fs, fill=INK)
    d.rectangle([Q(-16, 18), Q(16, -10)], outline=INK2, width=1)
    d.rectangle([Q(-2.2, 2.0), Q(2.2, -2.0)], outline=IRON, width=3)
    d.rectangle([Q(-1.2, 1.0), Q(1.2, -1.0)], fill=VOID)
    for (a, b) in [((-2.7, -2.6), (-0.7, 0.4)), ((2.7, -2.6), (0.7, 0.4)), ((-2.5, 7.2), (-0.7, 1.6)), ((2.5, 7.2), (0.7, 1.6))]:
        d.line([Q(*a), Q(*b)], fill=IRON, width=3)
    d.rectangle([Q(-1.3, 2.1), Q(1.3, -0.1)], outline=IRON, width=2)
    d.rectangle([Q(-0.9, 10.2), Q(0.9, 8.8)], fill=KIT)
    d.rectangle([Q(-4.5, 20.5), Q(4.5, 13.5)], outline=INK, width=3)
    d.ellipse([Q(-2.2, 19.7), Q(2.2, 15.3)], outline=INK2, width=2)
    d.rectangle([Q(-11.5, 18.6), Q(-4.5, 13.4)], outline=INK2, width=2)
    d.rectangle([Q(-10.5, 14.7), Q(-7.5, 13.9)], fill=IRON)
    d.rectangle([Q(-10.75, 18.4), Q(-8.25, 17.6)], fill=KIT)
    for k in range(4):
        d.rectangle([Q(-10.9 + k * 1.05, 18.2), Q(-10.3 + k * 1.05, 17.6)], fill=BONE, outline=INK)
    d.ellipse([Q(-3.7, -2.3), Q(-2.7, -3.3)], fill=KIT)
    for (x, y) in [(3.2, -3.0), (3.2, 0), (3.2, 3.0), (0, 3.0), (-3.2, 3.0), (0, -3.0), (-3.2, -3.0)]:
        d.ellipse([Q(x - 0.15, y + 0.15), Q(x + 0.15, y - 0.15)], fill=INK2)
    labels = [(Q(3.8, 0.6), "collar 2.4 x 2.0"), (Q(3.2, 5.5), "headframe legs"), (Q(1.5, 9.5), "winch"), (Q(-4.4, 21.5), "winding house 9 x 7"),
              (Q(-16, 15.5), "lean-to"), (Q(-16, 14.1), "bench"), (Q(-16, 17.9), "rack"), (Q(-1.9, -4.5), "listening post"), (Q(-6, 12.5), "charge point")]
    for (p, t) in labels:
        d.text(p, t, font=fs, fill=INK)
    d.text((ix + 10, iy + ih - 24), "machines are walked to the collar from the yard side (fence open there)", font=fs, fill=INK2)
    im.save(path)


def course_plan(path):
    """A4. The seed-54 corridor as walls, junction ids, depths, and the cut-back rule at nodes."""
    C, pos = course_layout(origin=(0, 0))
    xs = [v[0] for v in pos.values()]; ys = [v[1] for v in pos.values()]
    W, H = 1400, 1000
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    f, fs = font(20), font(14)
    s = min((W - 160) / (max(xs) - min(xs)), (H - 200) / (max(ys) - min(ys)))
    ox, oy = 80 - min(xs) * s, H - 120 + min(ys) * s

    def P(x, y):
        return (ox + x * s, oy - y * s)
    d.text((60, 14), "THE COURSE: phase2 seed 54, 8 junctions, %d passages, %d cells = %.0f m of passage, 1.8 m wide, walls 1.2 m (proposal)"
           % (len(C.passages), sum(p.length for p in C.passages.values()), 0.6 * sum(p.length for p in C.passages.values())), font=f, fill=INK)
    w = 1.8
    for p in C.passages.values():
        a, b = pos[p.near], pos[p.far]
        d.line([P(*a), P(*b)], fill=INK, width=int(w * s) + 4)
        d.line([P(*a), P(*b)], fill=PAPER, width=int(w * s))
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        d.text((P(mx, my)[0] + 6, P(mx, my)[1] - 8), f"{p.length}c = {p.length * 0.6:.1f} m", font=fs, fill=INK2)
    for k, (x, y) in pos.items():
        n = C.nodes[k]
        r = w / 2 * s + 6
        d.ellipse([P(x, y)[0] - r, P(x, y)[1] - r, P(x, y)[0] + r, P(x, y)[1] + r], fill=PAPER, outline=INK, width=2)
        col = WARM_DIM if k == C.shaft else (KIT if k == C.deposit else INK)
        d.text((P(x, y)[0] - 6, P(x, y)[1] - 9), str(k), font=fs, fill=col)
    d.text(P(pos[C.shaft][0], pos[C.shaft][1] - 4), "0 = root, the 'shaft' beacon post", font=fs, fill=WARM_DIM)
    d.text(P(pos[C.deposit][0], pos[C.deposit][1] - 4), f"{C.deposit} = the deposit leaf: a cargo crate", font=fs, fill=INK2)
    d.text((60, H - 70), "Walls are cut back 1.3 m at every node and the mouths are joined in angular order, so a leaf gets an end cap and a junction gets an open bay.", font=fs, fill=INK)
    d.text((60, H - 48), "Passages are 14-36 cells (tuning.PASSAGE_MIN/MAX_CELLS) = 8.4-21.6 m; the tree spans about 110 x 130 m. Seed 54 is one of eight seeds under 60 with no crossing passages.", font=fs, fill=INK)
    d.line([P(min(xs), min(ys) - 6), P(min(xs) + 20, min(ys) - 6)], fill=INK, width=3)
    d.text(P(min(xs), min(ys) - 8), "20 m", font=fs, fill=INK)
    im.save(path)


def shaft_section(path):
    """A5/A6. Section: headframe, collar, iron-lined top, rock shaft, the chamber. And the arithmetic of daylight."""
    W, H = 1100, 1300
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    f, fs, fm = font(20), font(14), font(13, True)
    s = 26.0
    ox, oy = 520, 330

    def P(x, z):
        return (ox + x * s, oy - z * s)
    d.text((40, 14), "SECTION through the shaft (proposal). Collar at 0, 16 m of shaft to the chamber roof, a 9.6 m chamber.", font=f, fill=INK)
    # ground
    d.rectangle([P(-18, 0), P(18, -40)], fill=(214, 207, 194))
    d.line([P(-18, 0), P(18, 0)], fill=INK, width=2)
    # shaft void
    d.rectangle([P(-1.2, 0.55), P(1.2, -16)], fill=VOID)
    # chamber
    d.ellipse([P(-7, -16), P(7, -25.6)], fill=VOID)
    d.rectangle([P(-7, -20.8), P(7, -25.6)], fill=VOID)
    d.line([P(-7, -25.6), P(7, -25.6)], fill=INK2, width=2)
    # iron lining
    d.rectangle([P(-1.35, 0.55), P(-1.2, -3)], fill=IRON); d.rectangle([P(1.2, 0.55), P(1.35, -3)], fill=IRON)
    # plinth + collar
    d.rectangle([P(-2.2, 0.4), P(-1.2, 0)], fill=(150, 140, 125)); d.rectangle([P(1.2, 0.4), P(2.2, 0)], fill=(150, 140, 125))
    d.rectangle([P(-1.5, 0.55), P(-1.2, 0.4)], fill=IRON); d.rectangle([P(1.2, 0.55), P(1.5, 0.4)], fill=IRON)
    # headframe (X-Z projection)
    for (a, b) in [((-2.7, 0), (-0.7, 9.4)), ((2.7, 0), (0.7, 9.4)), ((-2.5, 0), (-0.7, 9.4)), ((2.5, 0), (0.7, 9.4))]:
        d.line([P(*a), P(*b)], fill=IRON, width=4)
    for t in (0.33, 0.66):
        d.line([P(-2.7 + 2.0 * t, 9.4 * t), P(2.7 - 2.0 * t, 9.4 * t)], fill=IRON, width=3)
    d.rectangle([P(-1.3, 9.75), P(1.3, 9.4)], fill=IRON)
    for x in (-0.5, 0.5):
        d.ellipse([P(x - 0.9, 10.35 + 0.9), P(x + 0.9, 10.35 - 0.9)], outline=(120, 118, 112) if x > 0 else IRON, width=3)
    # cable and cage at z = -7
    d.line([P(0.5, 10.35), P(0.5, -4.0)], fill=(120, 118, 112), width=2)
    d.rectangle([P(-0.85, -5.8), P(0.85, -7.6)], outline=KIT, width=3)
    d.rectangle([P(-0.3, -7.05), P(0.3, -7.5)], fill=BONE)
    # flood cone
    d.polygon([P(0, 9.2), P(-1.2, -16), P(1.2, -16)], fill=(200, 210, 225))
    d.rectangle([P(-1.2, 0.55), P(1.2, -16)], outline=None)
    d.rectangle([P(-0.16, 9.35), P(0.16, 9.2)], fill=KIT)
    # machine on the chamber floor, in the pool
    d.polygon([P(0.6, -16), P(-1.6, -25.6), P(2.8, -25.6)], fill=(190, 200, 215))
    d.rectangle([P(0.3, -25.05), P(0.9, -25.5)], fill=BONE)
    d.rectangle([P(3.2, -25.05), P(3.8, -25.5)], fill=(60, 58, 55))
    # labels
    L = [(P(2.6, 10.4), "sheaves at +10.35 m; the live one bright"), (P(2.0, 8.9), "the flood: the teams' lamp aimed down the shaft, 12000 K (proposal)"),
         (P(2.6, 0.9), "collar +0.55, cast iron on a stone plinth"), (P(1.7, -1.6), "iron-lined 3 m"), (P(1.7, -9), "bare rock; guide rails full depth"),
         (P(-6.2, -5.5), "the cage on the modern winch,\n~20 s to the bottom"), (P(7.4, -18), "the shaft chamber: 14 m across, 9.6 m high"),
         (P(4.2, -25.0), "a machine in the pool of light, and one just outside it: black")]
    for (p, t) in L:
        d.text(p, t, font=fs, fill=INK)
    d.text((40, H - 250), "THE ARITHMETIC OF DAYLIGHT, and why the flood is proposed", font=f, fill=INK)
    d.text((40, H - 218), (
        "Overcast sky radiance at the direction's strength 1.0 is about 0.74 linear. Through a 2.4 x 2.0 m opening 16 m up,\n"
        "the floor sees a solid angle of 4.8 / 16^2 = 0.019 sr, so irradiance = 0.74 x 0.019 = 0.014, and albedo-0.30 rock\n"
        "returns 0.30 x 0.014 / pi = 0.0013 linear: below the direction's 0.02 'true black'. Real daylight at the bottom of a\n"
        "shaft is black. The probes' shaft frames used a 1400 W area light 7.6 m up, about ninety times the sky. So either the\n"
        "'12000 K daylight' underground is a fixture the teams bring (a flood at the collar, the shaft's own colour), or the\n"
        "shaft chamber is rendered at an exposure the surface is not. This board draws the flood and asks."), font=fm, fill=INK)
    im.save(path)


def srgb(v):
    v = max(0.0, min(1.0, v))
    return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def tone(rgb, s):
    # a crude film-ish curve so the strip reads like the renders rather than clipping
    out = []
    for c in rgb:
        x = c * s
        y = x / (1.0 + x) * 1.35
        out.append(int(255 * srgb(y)))
    return tuple(out)


def sky_strip(path):
    """A7. The six sky states as values: colour, strength, and what each is for."""
    rows = [("overcast (default)", SKY, 1.0, "the shaft's 12000 K; the surface's light IS the shaft's light"),
            ("drizzle", (0.56, 0.66, 0.86), 0.55, "everything wet; iron goes black and glossy"),
            ("heavy rain", (0.50, 0.58, 0.74), 0.32, "the flooding season's tell; the flood is on"),
            ("dusk", (0.42, 0.50, 0.74), 0.22, "the yard work light, the flood and the terminal come on; the sky still silhouettes the frame"),
            ("night", (0.30, 0.36, 0.55), 0.02, "the teams' lights are the only light on the surface, and the surface is allowed them"),
            ("low sun (ALTERNATIVE)", (0.42, 0.60, 1.00), 0.55, "what breaking 'no sun ever' costs: hard shadows, warm iron")]
    W, H = 1300, 120 + 96 * len(rows)
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    f, fs, fm = font(20), font(15), font(13, True)
    d.text((40, 14), "SKY: what it is and what it is allowed to do (proposal). No sun disc, ever; weather is the season axis; time of day is fixed per match.", font=f, fill=INK)
    for i, (name, col, s, why) in enumerate(rows):
        y = 70 + i * 96
        d.rectangle([40, y, 300, y + 80], fill=tone(col, s), outline=INK)
        d.text((320, y + 4), name, font=f, fill=INK)
        d.text((320, y + 34), f"colour ({col[0]:.2f}, {col[1]:.2f}, {col[2]:.2f})  x strength {s:g}   linear luminance {s * (0.2126 * col[0] + 0.7152 * col[1] + 0.0722 * col[2]):.3f}", font=fm, fill=INK2)
        d.text((320, y + 56), why, font=fs, fill=INK)
    im.save(path)


def pendant_screen(path, belief_png=None):
    """G2. Mock of the pendant's screen at a stop: belief only, the block keys, the sentence. 760 x 444."""
    W, H = 760, 444
    im = Image.new("RGB", (W, H), VOID)
    d = ImageDraw.Draw(im)
    f, fs, fm, fb = font(18), font(13), font(13, True), font(24)
    if belief_png and os.path.exists(belief_png):
        b = Image.open(belief_png).convert("RGB").resize((430, 250), Image.LANCZOS)
        im.paste(b, (16, 46))
    else:
        d.rectangle([16, 46, 446, 296], outline=WALKED, width=1)
    d.text((16, 12), "ITS MAP", font=f, fill=SENSED)
    d.text((110, 16), "what it thinks is there. the clock is stopped.", font=fs, fill=(140, 150, 160))
    d.rectangle([16, 46, 446, 296], outline=WALKED, width=1)
    # predicates with values (CAVE-BLOCKS 2.1 names)
    x0 = 470
    d.text((x0, 46), "IT KNOWS", font=fs, fill=(140, 150, 160))
    preds = [("unexplored branch exists", "YES", SENSED), ("lost  (theta 12 > 16?)", "NO", (140, 150, 160)), ("carrying cargo", "NO", (140, 150, 160)), ("the machinery is loud", "NO", (140, 150, 160))]
    for i, (p, v, c) in enumerate(preds):
        y = 70 + i * 26
        d.text((x0, y), p, font=fm, fill=(200, 205, 210))
        d.text((x0 + 230, y), v, font=fm, fill=c)
    d.text((x0, 190), "WHAT IT CAN DO  (a key each)", font=fs, fill=(140, 150, 160))
    keys = [("1", "take a branch"), ("2", "go back to the beacon"), ("3", "freeze until it passes"), ("4", "fetch from a deposit"), ("5", "hold"), ("6", "carry on")]
    for i, (k, a) in enumerate(keys):
        y = 212 + i * 22
        d.rectangle([x0, y, x0 + 18, y + 18], outline=BONE, width=1)
        d.text((x0 + 4, y), k, font=fm, fill=BONE)
        d.text((x0 + 28, y + 1), a, font=fm, fill=(220, 222, 225) if i == 0 else (150, 155, 160))
    # the sentence
    d.rectangle([0, 356, W, H], fill=(12, 16, 22))
    d.text((16, 366), "STOPPED AT A JUNCTION. TWO WAYS ON.", font=fb, fill=BONE)
    d.text((16, 402), "it has not been told what to do here. press a key; it will be written down and the clock will start again.", font=fs, fill=(170, 175, 180))
    d.text((W - 150, 12), "0:00  stopped", font=f, fill=(170, 175, 180))
    im.save(path)


# -------------------------------------------------------------------------------------------
def descent_strip(path):
    names = ["23_descent_1_collar", "24_descent_2_halfway", "25_descent_3_lookup", "26_descent_4_chamber"]
    ims = [Image.open(os.path.join(HERE, n + ".png")).convert("RGB") for n in names if os.path.exists(os.path.join(HERE, n + ".png"))]
    if len(ims) < 2:
        return
    w = 480
    ims = [i.resize((w, int(i.height * w / i.width)), Image.LANCZOS) for i in ims]
    H = sum(i.height for i in ims) + 8 * (len(ims) - 1) + 60
    out = Image.new("RGB", (w, H), VOID)
    d = ImageDraw.Draw(out)
    d.text((10, 8), "THE DESCENT: 20 s from full authority to none", font=font(16), fill=BONE)
    d.text((10, 30), "collar / halfway / the sky shrinking / the pool below", font=font(12), fill=(160, 165, 170))
    y = 52
    for i in ims:
        out.paste(i, (0, y)); y += i.height + 8
    out.save(path)


def sky_renders_strip(path):
    names = [("29_sky_overcast", "overcast"), ("30_sky_drizzle", "drizzle"), ("31_sky_rain", "rain"), ("32_sky_dusk", "dusk"), ("33_sky_night", "night"), ("34_sky_sun_alt", "sun (alternative)")]
    ims = [(Image.open(os.path.join(HERE, n + ".png")).convert("RGB"), t) for n, t in names if os.path.exists(os.path.join(HERE, n + ".png"))]
    if len(ims) < 2:
        return
    w = 480
    cols = 3
    rows = (len(ims) + cols - 1) // cols
    h = int(ims[0][0].height * w / ims[0][0].width)
    out = Image.new("RGB", (w * cols + 8 * (cols - 1), (h + 28) * rows), VOID)
    d = ImageDraw.Draw(out)
    for i, (im, t) in enumerate(ims):
        r, c = divmod(i, cols)
        x, y = c * (w + 8), r * (h + 28)
        out.paste(im.resize((w, h), Image.LANCZOS), (x, y + 24))
        d.text((x + 6, y + 4), t, font=font(15), fill=BONE)
    out.save(path)


def teach_ghost(path):
    """G1. The believed graph over the demonstration wide: what the machine thinks the course is, in GHOST, unlit."""
    src = os.path.join(HERE, "44_teach_wide.png")
    pj = os.path.join(HERE, "_teach_proj.json")
    if not (os.path.exists(src) and os.path.exists(pj)):
        return
    im = Image.open(src).convert("RGB")
    J = json.load(open(pj))
    W, H = im.size
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    nodes = {int(k): (v[0] * W, (1 - v[1]) * H) for k, v in J["nodes"].items()}
    # 'believed' = the walked part: root to the stop, drawn with a deliberate drift of a few px per hop
    from phase2.truth.corridor import Corridor
    C = Corridor(54)
    stop = J["stop"]
    path_nodes = []
    k = stop
    while k is not None:
        path_nodes.append(k)
        k = C.nodes[k].parent
        k = C.passages[k].near if k is not None else None
    path_nodes.reverse()
    drift = 0.0
    prev = None
    for i, n in enumerate(path_nodes):
        x, y = nodes[n]
        drift += 4.0
        pt = (x + drift * 0.8, y + drift * 0.5)
        if prev:
            d.line([prev, pt], fill=(*GHOST, 200), width=3)
        d.ellipse([pt[0] - 5, pt[1] - 5, pt[0] + 5, pt[1] + 5], fill=(*SENSED, 220))
        prev = pt
    # the onward passages it believes exist at the stop: short stubs
    x, y = prev
    for pid in C.children(stop):
        far = C.passages[pid].far
        fx, fy = nodes[far]
        ex, ey = x + (fx - x) * 0.35, y + (fy - y) * 0.35
        d.line([(x, y), (ex, ey)], fill=(*GHOST, 120), width=2)
    out = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
    dd = ImageDraw.Draw(out)
    dd.text((12, 10), "what it believes the course is (GHOST, unlit, drawn) over what is there (rendered)", font=font(15), fill=GHOST)
    out.save(path)


def course_overlay(path):
    src = os.path.join(HERE, "14_course_oblique.png")
    pj = os.path.join(HERE, "_course_proj.json")
    if not (os.path.exists(src) and os.path.exists(pj)):
        return
    im = Image.open(src).convert("RGB")
    J = json.load(open(pj))
    W, H = im.size
    d = ImageDraw.Draw(im)
    nodes = {int(k): (v[0] * W, (1 - v[1]) * H) for k, v in J["nodes"].items()}
    for a, b in J["passages"]:
        d.line([nodes[a], nodes[b]], fill=WARM_DIM, width=2)
    for k, (x, y) in nodes.items():
        r = 5 if k in (J["shaft"], J["deposit"]) else 3
        d.ellipse([x - r, y - r, x + r, y + r], fill=BONE if k == J["shaft"] else (KIT if k == J["deposit"] else WARM_DIM))
        d.text((x + 6, y - 7), str(k), font=font(13), fill=BONE)
    d.text((12, 10), "the graph over the course: node ids as phase2 numbers them; root pale, deposit leaf grey", font=font(15), fill=BONE)
    im.save(path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--snaps", default=None, help="dir with belief_inset.png (a crop of a phase1 snapshot)")
    ap.add_argument("--composites", action="store_true")
    a = ap.parse_args()
    if not a.composites:
        pithead_plan(os.path.join(HERE, "00_pithead_plan.png"))
        course_plan(os.path.join(HERE, "00_course_plan.png"))
        shaft_section(os.path.join(HERE, "00_shaft_section.png"))
        sky_strip(os.path.join(HERE, "00_sky_values.png"))
        pendant_screen(os.path.join(HERE, "00_pendant_screen.png"), os.path.join(a.snaps, "belief_only.png") if a.snaps else None)
        print("diagrams written")
    else:
        descent_strip(os.path.join(HERE, "23_descent_strip.png"))
        sky_renders_strip(os.path.join(HERE, "29_sky_renders_strip.png"))
        teach_ghost(os.path.join(HERE, "44_teach_wide_ghost.png"))
        course_overlay(os.path.join(HERE, "14_course_oblique_graph.png"))
        print("composites written")
