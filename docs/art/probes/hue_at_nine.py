"""Is team identity really the only channel that survives nine pixels? Measure it.

pixel_ladder.py showed a bronze row and a pale row and I called that "team survives at
nine pixels". This checks it properly, in CIE L*a*b*, and splits the machine into two
populations because they behave completely differently:

  PAINT     the machine's mid-bright pixels -- lit surface, so whatever colour the scene
            light is, the paint is wearing it
  EMISSIVE  its top 3% brightest pixels -- self-luminous, so scene light cannot wash them

Delta-E >= 2.3 is the "just noticeable" threshold; >= 5 is "obviously a different colour
across a room". Reported per rung of the ladder.
"""
import os
import sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixel_ladder import load, machine_bbox, crop_square, down, lum


def lab(rgb):
    def f(t): return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    def li(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (li(max(c, 0.0)) for c in rgb)
    X = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    Y = (0.2126 * r + 0.7152 * g + 0.0722 * b)
    Z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    fx, fy, fz = f(X), f(Y), f(Z)
    return np.array([116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)])


def populations(name, n):
    a = load(name)
    c = crop_square(a, machine_bbox(a))
    d = down(c, n)
    l = lum(d)
    hi = np.percentile(l, 97)
    mid = (l > np.percentile(l, 60)) & (l <= hi)
    emis = l >= hi
    return d[mid].mean(axis=0), d[emis].mean(axis=0)


SETS = {
    "chassis (are the four classes distinguishable?)":
        [("scout", "01_scout_default.png"), ("surveyor", "02_surveyor_default.png"),
         ("hauler", "03_hauler_default.png"), ("swimmer", "04_swimmer_default.png")],
    "state (team, loadout, death)":
        [("player", "02_surveyor_default.png"), ("bare", "05_surveyor_bare.png"),
         ("RIVAL", "06_surveyor_loud.png"), ("salvage", "08_wreck_salvage.png")],
}

for setname, items in SETS.items():
    print(f"\n=== {setname} ===")
    for n in (9, 22, 56):
        paint, emis = {}, {}
        for k, f in items:
            p, e = populations(f, n)
            paint[k], emis[k] = p, e
        print(f"\n  --- {n} px ---")
        for k, _ in items:
            lp, le = lab(paint[k]), lab(emis[k])
            print(f"    {k:<9} paint L*{lp[0]:6.1f} a*{lp[1]:6.1f} b*{lp[2]:6.1f}"
                  f"   |   emissive L*{le[0]:6.1f} a*{le[1]:6.1f} b*{le[2]:6.1f}")
        ks = [k for k, _ in items]
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                dp = np.linalg.norm(lab(paint[ks[i]]) - lab(paint[ks[j]]))
                de = np.linalg.norm(lab(emis[ks[i]]) - lab(emis[ks[j]]))
                tag = "   <== THE TEAM PAIR" if {"player", "RIVAL"} <= {ks[i], ks[j]} else ""
                print(f"      dE {ks[i]:<8}/{ks[j]:<8}  paint {dp:6.1f}   emissive {de:6.1f}{tag}")
