"""Build one self-contained page showing the three Godot views.

Embeds every frame as a data URI so the page needs nothing beside it.

Run: python spikes/godot/_views_page.py OUT.html
"""
from __future__ import annotations

import base64
import html
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WIDTH = 900
QUALITY = 80

# (path relative to spikes/godot, caption)
CAVE = [
    ("cave/shots/01_wide_passage.png", "A passage under one lamp. Nine-tenths of the frame is true black by design."),
    ("cave/shots/03_underfoot.png", "Underfoot. The floor the designer called out, after the rebuild."),
    ("cave/shots/08_waterline.png", "The waterline. Standing water with a real surface and an edge."),
    ("cave/shots/04_chamber.png", "A chamber, where the lamp stops reaching before the walls do."),
    ("cave/shots/11_set_line.png", "A line of sets. Timber and iron the ancients left."),
    ("cave/shots/05_two_registers.png", "Both registers in one frame: the players' kit against old iron."),
    ("cave/shots/07_junction.png", "A junction."),
    ("cave/shots/12_crown.png", "The crown, looking up."),
    ("cave/shots/09_machine_ground.png", "Deep machine ground."),
    ("cave/shots/06_falloff_to_black.png", "The falloff. What the light economy actually looks like."),
]
CAVE_PAIRS = [
    ("cave/shots/photoreal/pairs/p1_underfoot_macro.png", "Underfoot, before above and after below. The before is what you walked."),
    ("cave/shots/photoreal/pairs/p2_wet_floor_water.png", "Wet floor and standing water, before above, after below."),
    ("cave/shots/photoreal/pairs/p3_wall_lamp_dist.png", "A wall at lamp distance, before above, after below."),
    ("cave/shots/photoreal/pairs/p7_ballast_gauge.png", "Ballast and gauge, before above, after below."),
]
SURFACE = [
    ("surface/shots/photoreal/after/p10_site_wide.png", "The pit-head. The only place in the game with sky."),
    ("surface/shots/photoreal/after/p03_yard_working.png", "The yard at working distance."),
    ("surface/shots/photoreal/after/p02_underfoot_45.png", "Underfoot in the yard, with two machines on the hardstanding."),
    ("surface/shots/photoreal/after/p04_hardstanding.png", "Hardstanding: slab joints, spalling, oil, repaired bays."),
    ("surface/shots/photoreal/after/p05_rain_underfoot.png", "Rain. The surfaces wet rather than just particles falling."),
    ("surface/shots/photoreal/after/p08_shaft_collar.png", "The shaft collar, where the descent starts."),
    ("surface/shots/photoreal/after/p09_shaft_mouth.png", "The shaft mouth. Daylight ends here."),
    ("surface/shots/photoreal/after/p12_dusk_yard.png", "Dusk, which is the prettier frame because it hides two thirds of the yard."),
    ("surface/shots/photoreal/after/p07_rusted_iron.png", "Rusted iron close up."),
    ("surface/shots/photoreal/after/p11_road_kerb.png", "Road and kerb."),
]
CLOUD = [
    ("cloud/shots/18_fix_two_corridors_dense.png", "The fix, dense. The same passage drawn twice, in two places, because old returns are never re-registered."),
    ("cloud/shots/02_late_full_match.png", "A whole match of belief, accumulated."),
    ("cloud/shots/03_low_orbit_surfaces.png", "Low orbit. Banks of returns read as surfaces without any mesh."),
    ("cloud/shots/05_drift_smear.png", "Drift. The cloud smears because every point is placed at a pose that is wrong by a growing amount."),
    ("cloud/shots/01_early_sparse.png", "Early in the match. An honest picture of how little the machine knows."),
    ("cloud/shots/10_spoof_after.png", "After the spoof. A fix on a lie moves the estimate thirty cells and the cloud tears."),
    ("cloud/shots/12_dense_1m.png", "One million points, eight milliseconds, three draw calls."),
    ("cloud/shots/14_both_registers.png", "Both registers: the real cave turned down, belief additive over it."),
    ("cloud/shots/04_macro_true_disc.png", "Macro. Every disc is one return, facing back along the ray that measured it."),
    ("cloud/shots/20_low_orbit_dense.png", "Low orbit, dense."),
]
SECTIONS = [
    ("truth", "The cave", "Ground truth, generated from a seed and lit by one lamp. 107 frames a second with 33,470 props.", CAVE),
    ("change", "What changed today", "Before above, after below, from identical camera positions.", CAVE_PAIRS),
    ("surface", "The pit-head", "The surface, where machines are kept, taught and sent down. Daylight, and the only sky in the game.", SURFACE),
    ("belief", "The agent's view", "The point cloud. Belief, not truth. It renders with no lights in the scene at all.", CLOUD),
]


def uri(rel: str) -> str | None:
    from PIL import Image
    p = ROOT / rel
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
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "views.html")
    body, nav, n = [], [], 0
    for key, title, blurb, items in SECTIONS:
        figs = []
        for rel, cap in items:
            u = uri(rel)
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
                    f'<div class="grid">{"".join(figs)}</div></section>')

    css = """
:root{--ink:#0b0908;--panel:#141110;--edge:#282221;--bone:#e9e0d2;--dust:#9a9084;
      --faint:#6b6259;--ember:#c8702f;--cyan:#7fc4d8}
*{box-sizing:border-box}
body{margin:0;background:var(--ink);color:var(--bone);
 font:16px/1.65 "IBM Plex Serif",Georgia,serif}
header{padding:40px 26px 22px;border-bottom:1px solid var(--edge);background:var(--panel)}
h1{font-family:"Saira Condensed",Impact,sans-serif;font-weight:700;font-size:40px;
 letter-spacing:.02em;text-transform:uppercase;margin:0 0 6px;line-height:1}
h1 span{color:var(--ember)}
.sub{margin:0;color:var(--dust);max-width:66ch;font-size:15.5px}
.run{margin:18px 0 0;padding:12px 14px;background:var(--ink);border:1px solid var(--edge);
 font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;color:var(--dust);
 overflow-x:auto;white-space:pre;line-height:1.7}
nav{padding:14px 26px;border-bottom:1px solid var(--edge);position:sticky;top:0;
 background:#0b0908ee;z-index:5}
nav a{color:var(--ember);text-decoration:none;margin-right:20px;
 font-family:"Saira Condensed",sans-serif;text-transform:uppercase;letter-spacing:.05em;
 font-size:14px}
nav a:hover,nav a:focus-visible{color:var(--bone);outline:none}
main{padding:0 26px 90px;max-width:1700px}
section{padding-top:44px}
h2{font-family:"Saira Condensed",sans-serif;font-weight:700;font-size:30px;margin:0 0 4px;
 text-transform:uppercase;letter-spacing:.01em}
.blurb{margin:0 0 16px;color:var(--dust);max-width:70ch}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:20px}
figure{margin:0;background:var(--panel);border:1px solid var(--edge)}
figure img{display:block;width:100%;background:#000}
figcaption{padding:10px 12px;font-size:13.5px;color:var(--faint);line-height:1.5}
#belief figcaption{color:#8fb6c4}
@media (max-width:640px){.grid{grid-template-columns:1fr}h1{font-size:30px}}
"""
    head = ('<title>Blindside in Three Dimensions</title>'
            '<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
            'family=Saira+Condensed:wght@600;700&family=IBM+Plex+Serif:wght@400;600&'
            'family=IBM+Plex+Mono:wght@400&display=swap">'
            f'<style>{css}</style>')
    hdr = (
        '<header><h1>Blindside <span>in three dimensions</span></h1>'
        '<p class="sub">Three views, all generated from a seed in code, all running in Godot 4.7 '
        'on this machine. Nothing here is modelled by hand and nothing is a Blender render. '
        f'{n} frames at 1920&times;1080.</p>'
        '<div class="run">Walk them yourself:\n'
        '  godot --path spikes/godot/cave    --resolution 1920x1080\n'
        '  godot --path spikes/godot/surface --resolution 1920x1080 -- --mode=free\n'
        '  godot --path spikes/godot/cloud   --resolution 1920x1080\n\n'
        'godot = ~/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64.exe\n'
        'In the yard, 1 / 2 / 3 swap the weather. WASD and the mouse to move.</div></header>')
    out.write_text(head + hdr + f'<nav>{"".join(nav)}</nav><main>{"".join(body)}</main>',
                   encoding="utf-8", newline="\n")
    print(f"{out}  {out.stat().st_size/1e6:.1f} MB  {n} frames")


if __name__ == "__main__":
    main()
