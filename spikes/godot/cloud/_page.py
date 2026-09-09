"""One self-contained page of the belief point cloud, every frame embedded.

Run: python spikes/godot/cloud/_page.py OUT.html
"""
from __future__ import annotations

import base64
import html
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "shots"
WIDTH = 1200
QUALITY = 82

GROUPS = [
    ("what", "What the machine believes",
     "Every disc is one sensor return, drawn where the machine thinks it happened, facing back "
     "along the ray that measured it. Nothing here is the real cave. This is the only view the "
     "player is allowed to watch live.",
     [("01_early_sparse.png", "1:40. How little it knows. Mostly ground it has walked, a few pinged walls."),
      ("02_late_full_match.png", "8:00. The whole believed map, at the end of a match."),
      ("03_low_orbit_surfaces.png", "5:00, a low orbit. Banks of returns start to read as surfaces with no mesh anywhere."),
      ("04_macro_true_disc.png", "Close in, at the 45 mm disc the art direction specifies. This is why that number is wrong."),
      ]),
    ("wrong", "The three things belief does that truth cannot",
     "Drift, the fix, and the lie. These are the game, and none of them can be drawn from ground truth.",
     [("05_drift_smear.png", "Drift. Four minutes of dead reckoning, so every return is placed at a pose that is wrong by a growing amount."),
      ("06_fix_before.png", "7:07, one second before a fix. One passage, drawn twice, eight cells apart."),
      ("07_fix_after.png", "7:13, the same camera. The fix has closed it. The old returns were never moved."),
      ("08_fix_two_corridors.png", "8:00. A doubling no fix will ever close: 17.4 cells apart, both drawn, no annotation."),
      ("09_spoof_before.png", "2:21. One second before the rival's lie lands."),
      ("10_spoof_after.png", "2:24, the same camera. The map folds: 33 cells of error, eleven times its own stated uncertainty."),
      ]),
    ("dense", "Sparse against dense, which is the real finding",
     "A whole match of the toy simulation produces 5,663 points and only 1,007 of them are wall "
     "hits. Everything about this view improves with more returns. The renderer is not the "
     "constraint. The sensor is, and how much the machine can perceive is still an open decision.",
     [("18_fix_two_corridors_dense.png", "The same doubled passage at a million points. This is the frame that reads."),
      ("12_dense_1m.png", "One million points. Eight milliseconds, three draw calls."),
      ("13_dense_2m.png", "Two million, the practical ceiling. The limit is the area the discs cover, not how many there are."),
      ("20_low_orbit_dense.png", "A low orbit at a million. Banks of discs, unmistakably surfaces."),
      ("11_dense_100k.png", "A hundred thousand points, for scale between the two."),
      ("19_spoof_after_dense.png", "The lie, dense."),
      ]),
    ("both", "Belief against truth",
     "The two registers together. They never agree in shape, and by the end of a match they "
     "barely overlap at all.",
     [("14_both_registers.png", "The real cave turned down to a third, the cloud additive over it."),
      ("15_truth_only.png", "Truth alone, and it only reads because it was given a light that does not exist in the fiction."),
      ]),
    ("rejected", "Rejected, and kept for the record",
     "Alternatives that were built and measured rather than argued about.",
     [("17_points_baseline.png", "Hardware points. Nearly twice as cheap and it is the thing the art direction rules out."),
      ("16_solid_blend.png", "Opaque discs with depth writing, instead of additive."),
      ("90_probe_600mm_flat_disc.png", "Constant 600 mm discs with no minimum screen size: the bare rule, unhelped."),
      ("91_probe_walked_flat.png", "Walked returns laid flat on the floor instead of along the ray."),
      ]),
]


def uri(name: str) -> str | None:
    from PIL import Image
    p = SHOTS / name
    if not p.is_file():
        return None
    try:
        im = Image.open(p)
        im.load()
        im = im.convert("RGB")
    except Exception:
        return None
    if im.width > WIDTH:
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=QUALITY, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode("ascii")


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "cloud.html")
    body, nav, n = [], [], 0
    for key, title, blurb, items in GROUPS:
        figs = []
        for name, cap in items:
            u = uri(name)
            if u is None:
                continue
            n += 1
            figs.append(f'<figure><img loading="lazy" src="{u}" alt="{html.escape(cap)}">'
                        f'<figcaption>{html.escape(cap)}</figcaption></figure>')
        if not figs:
            continue
        nav.append(f'<a href="#{key}">{html.escape(title)}</a>')
        body.append(f'<section id="{key}"><h2>{html.escape(title)}</h2>'
                    f'<p class="blurb">{html.escape(blurb)}</p>'
                    f'<div class="stack">{"".join(figs)}</div></section>')

    css = """
:root{--void:#05070a;--panel:#0b1016;--edge:#16222c;--ice:#cfe6ef;--dust:#7f95a1;
      --faint:#5b7280;--cyan:#7fc4d8}
*{box-sizing:border-box}
body{margin:0;background:var(--void);color:var(--ice);
 font:16px/1.65 "IBM Plex Serif",Georgia,serif}
header{padding:44px 26px 24px;border-bottom:1px solid var(--edge)}
h1{font-family:"Saira Condensed",Impact,sans-serif;font-weight:700;font-size:42px;
 letter-spacing:.02em;text-transform:uppercase;margin:0 0 10px;line-height:1}
h1 span{color:var(--cyan)}
.sub{margin:0 0 6px;color:var(--dust);max-width:68ch;font-size:16px}
.facts{display:flex;flex-wrap:wrap;gap:26px;margin-top:20px;
 font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;color:var(--faint);
 font-variant-numeric:tabular-nums}
.facts b{display:block;color:var(--cyan);font-size:19px;font-weight:600;margin-bottom:2px}
nav{padding:13px 26px;border-bottom:1px solid var(--edge);position:sticky;top:0;
 background:#05070aee;z-index:5}
nav a{color:var(--cyan);text-decoration:none;margin-right:20px;
 font-family:"Saira Condensed",sans-serif;text-transform:uppercase;letter-spacing:.05em;
 font-size:13.5px}
nav a:hover,nav a:focus-visible{color:var(--ice);outline:none}
main{padding:0 26px 90px;max-width:1400px}
section{padding-top:46px}
h2{font-family:"Saira Condensed",sans-serif;font-weight:700;font-size:29px;margin:0 0 6px;
 text-transform:uppercase}
.blurb{margin:0 0 20px;color:var(--dust);max-width:72ch}
.stack{display:flex;flex-direction:column;gap:22px}
figure{margin:0;background:var(--panel);border:1px solid var(--edge)}
figure img{display:block;width:100%;background:#000}
figcaption{padding:11px 14px;font-size:14px;color:var(--faint);line-height:1.55}
@media (max-width:640px){h1{font-size:29px}}
"""
    head = ('<title>What the Machine Believes</title>'
            '<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
            'family=Saira+Condensed:wght@600;700&family=IBM+Plex+Serif:wght@400;600&'
            'family=IBM+Plex+Mono:wght@400;600&display=swap">'
            f'<style>{css}</style>')
    hdr = (
        '<header><h1>What the machine <span>believes</span></h1>'
        '<p class="sub">The agent&rsquo;s own view, in three dimensions, running in Godot. '
        'Every disc is one sensor return placed where the machine thinks it happened. None of '
        'it is ground truth, which is the point: this is the only view a player is allowed to '
        'watch during a match.</p>'
        '<p class="sub">It renders with no lights in the scene at all &mdash; ambient off, no '
        'fog, no shadows &mdash; and stays legible from every angle. The real cave cannot do '
        'that.</p>'
        '<div class="facts">'
        '<span><b>3</b>draw calls, at any size</span>'
        '<span><b>1M</b>points at 8 ms</span>'
        '<span><b>2M</b>practical ceiling</span>'
        '<span><b>64 B</b>per point</span>'
        '<span><b>5,663</b>points in a real match</span>'
        '<span><b>1,007</b>of those are wall hits</span>'
        '</div></header>')
    out.write_text(head + hdr + f'<nav>{"".join(nav)}</nav><main>{"".join(body)}</main>',
                   encoding="utf-8", newline="\n")
    print(f"{out}  {out.stat().st_size/1e6:.1f} MB  {n} frames")


if __name__ == "__main__":
    main()
