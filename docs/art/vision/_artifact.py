"""Build a single self-contained page of the whole vision board.

Reads the same notes _assemble.py reads, embeds every image as a data URI at 700 px, and
writes one HTML file that needs nothing beside it. About 5 MB.

Run: python docs/art/vision/_artifact.py OUT.html
"""
from __future__ import annotations

import base64
import html
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _assemble as A  # noqa: E402

WIDTH = 700
QUALITY = 76
CODE = re.compile(r"\b([A-H]\d{1,2})\b")


def data_uri(src: Path) -> str | None:
    from PIL import Image
    try:
        im = Image.open(src)
        im.load()
        im = im.convert("RGB")
    except Exception:
        return None
    if im.width > WIDTH:
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=QUALITY, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def split_title(title: str) -> tuple[str, str]:
    """The inventory's own index code (A1, B17, D4) and the name without it."""
    m = CODE.search(title)
    code = m.group(1) if m else ""
    name = title
    if code:
        name = re.sub(r"\s*\(" + code + r"\)\s*$", "", name)
        name = re.sub(r"^" + code + r"\s*[/—–-]*\s*", "", name)
    name = re.sub(r"^[a-z0-9-]+/\s*[—–-]\s*", "", name)
    name = re.sub(r"^[a-z0-9-]+\s+[—–-]\s+", "", name)
    return code, name.strip(" —–-/")


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "vision-board.html")
    sections, nav = [], []
    n_img = n_con = 0

    for key, title, blurb in A.GROUPS:
        concepts = A.parse(key)
        if not concepts:
            continue
        cards = []
        count = 0
        for c in concepts:
            code, name = split_title(c["title"])
            frames = []
            for im in c["images"]:
                uri = data_uri(im["path"])
                if uri is None:
                    continue
                k = im["kind"]
                chip = (f'<span class="chip {k.replace(" ", "")}">{k}</span>') if k else ""
                frames.append(
                    f'<figure><img loading="lazy" src="{uri}" alt="{html.escape(name)}">'
                    f'<figcaption>{chip}<span class="fn">{html.escape(im["name"])}</span>'
                    f'<span class="int">{html.escape(im["intent"] or "")}</span>'
                    f'</figcaption></figure>')
                count += 1
            if not frames:
                continue
            n_con += 1
            mark = f'<span class="code">{code}</span>' if code else ""
            cards.append(f'<section class="concept"><h3>{mark}{html.escape(name)}'
                         f'<span class="n">{len(frames)}</span></h3>'
                         f'<div class="grid">{"".join(frames)}</div></section>')
        n_img += count
        nav.append(f'<a href="#{key}"><span>{html.escape(title)}</span>'
                   f'<em>{count}</em></a>')
        sections.append(
            f'<section class="group" id="{key}"><header class="gh">'
            f'<h2>{html.escape(title)}</h2><p>{html.escape(blurb)}</p>'
            f'<p class="meta">{count} renders &middot; {len(cards)} concepts</p>'
            f'</header>{"".join(cards)}</section>')

    css = """
:root{
  --iron:#0c0806; --pit:#141010; --plate:#1b1614; --edge:#2b2320;
  --bone:#e8dfd0; --dust:#9d9184; --faint:#6d645b;
  --ember:#c8702f; --shaft:#8fb0dc;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--iron);color:var(--bone);
  font:16px/1.6 "IBM Plex Serif",Georgia,serif;
  -webkit-font-smoothing:antialiased}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
.wrap{display:grid;grid-template-columns:250px minmax(0,1fr);gap:0;align-items:start}
@media (max-width:900px){.wrap{grid-template-columns:1fr}}

aside{position:sticky;top:0;height:100vh;padding:28px 20px;border-right:1px solid var(--edge);
  display:flex;flex-direction:column;gap:22px;overflow:auto;background:var(--pit)}
@media (max-width:900px){aside{position:static;height:auto;border-right:none;
  border-bottom:1px solid var(--edge)}}
.mast{font-family:"Saira Condensed",Impact,sans-serif;font-weight:700;
  font-size:30px;line-height:.98;letter-spacing:.02em;text-transform:uppercase;
  color:var(--bone);text-wrap:balance}
.mast em{display:block;font-style:normal;font-size:12px;font-weight:500;
  letter-spacing:.22em;color:var(--ember);margin-top:8px}
.thesis{font-size:13.5px;line-height:1.55;color:var(--dust);margin:0;
  border-left:2px solid var(--ember);padding-left:11px}
.tally{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--faint);
  display:flex;flex-direction:column;gap:3px;font-variant-numeric:tabular-nums}
.tally b{color:var(--bone);font-weight:600}
nav{display:flex;flex-direction:column;gap:1px;margin-top:auto}
nav a{display:flex;justify-content:space-between;gap:10px;align-items:baseline;
  text-decoration:none;color:var(--dust);padding:7px 9px;border-radius:2px;
  font-family:"Saira Condensed",sans-serif;font-size:14.5px;letter-spacing:.03em;
  text-transform:uppercase;border-left:2px solid transparent}
nav a:hover,nav a:focus-visible{color:var(--bone);background:var(--plate);
  border-left-color:var(--ember);outline:none}
nav em{font-family:"IBM Plex Mono",monospace;font-style:normal;font-size:11px;
  color:var(--faint);font-variant-numeric:tabular-nums}

main{padding:0 30px 100px;min-width:0}
.lede{padding:46px 0 8px;max-width:64ch}
.lede h1{font-family:"Saira Condensed",sans-serif;font-weight:600;font-size:15px;
  letter-spacing:.2em;text-transform:uppercase;color:var(--faint);margin:0 0 14px}
.lede p{margin:0 0 12px;color:var(--dust);font-size:15.5px}
.lede strong{color:var(--bone);font-weight:600}

.group{padding-top:54px;scroll-margin-top:10px}
.gh{border-top:1px solid var(--edge);padding-top:16px;margin-bottom:6px;max-width:70ch}
.gh h2{font-family:"Saira Condensed",sans-serif;font-weight:700;font-size:34px;
  line-height:1.05;letter-spacing:.01em;margin:0 0 6px;text-transform:uppercase;
  text-wrap:balance}
.gh p{margin:0;color:var(--dust);font-size:15px}
.gh .meta{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--faint);
  margin-top:8px;font-variant-numeric:tabular-nums}

.concept{margin-top:34px}
.concept h3{display:flex;align-items:baseline;gap:11px;margin:0 0 13px;
  font-family:"Saira Condensed",sans-serif;font-weight:600;font-size:19px;
  letter-spacing:.04em;text-transform:uppercase;color:var(--bone);
  border-bottom:1px solid var(--edge);padding-bottom:8px}
.code{font-family:"IBM Plex Mono",monospace;font-size:11px;font-weight:600;
  letter-spacing:.06em;color:var(--iron);background:var(--dust);
  padding:2px 6px;border-radius:1px;flex:none}
.concept h3 .n{margin-left:auto;font-family:"IBM Plex Mono",monospace;font-size:11px;
  color:var(--faint);font-weight:400;letter-spacing:0}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:18px}
figure{margin:0;display:flex;flex-direction:column;background:var(--pit);
  border:1px solid var(--edge)}
figure img{display:block;width:100%;height:auto;background:#000}
figcaption{padding:9px 11px 12px;display:flex;flex-direction:column;gap:5px}
.chip{align-self:flex-start;font-family:"IBM Plex Mono",monospace;font-size:9.5px;
  text-transform:uppercase;letter-spacing:.12em;padding:2px 6px;border-radius:1px}
.chip.clear{color:var(--shaft);border:1px solid rgba(143,176,220,.4)}
.chip.insitu{color:var(--ember);border:1px solid rgba(200,112,47,.45)}
.fn{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--dust);
  word-break:break-all}
.int{font-size:13.5px;line-height:1.5;color:var(--faint)}
"""

    # The Artifact host supplies <!doctype>, <head> and <body>; this file is the content.
    head = (
        '<title>Blindside Vision Board</title>'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Saira+Condensed:wght@500;600;700&family=IBM+Plex+Serif:wght@400;600&'
        'family=IBM+Plex+Mono:wght@400;600&display=swap">'
        f'<style>{css}</style>')

    aside = (
        '<aside>'
        '<div class="mast">Blindside<em>Vision Board</em></div>'
        '<p class="thesis">A drowned iron mine that never stopped working, '
        'photographed by one lamp somebody carried in.</p>'
        f'<div class="tally"><span><b>{n_img}</b> renders</span>'
        f'<span><b>{n_con}</b> concepts</span>'
        '<span><b>2026-09-08</b></span></div>'
        f'<nav>{"".join(nav)}</nav></aside>')

    lede = (
        '<div class="lede"><h1>What this is</h1>'
        '<p>Every art concept in the game, surface and underground. Each concept gets a '
        '<strong>clear</strong> view, lit so the thing can be seen, and an '
        '<strong>in situ</strong> view in the game&rsquo;s own light. The two tags are the '
        'world&rsquo;s only two light sources: the shaft&rsquo;s cold daylight, and the lamp '
        'a machine carries.</p>'
        '<p>The codes are the inventory&rsquo;s own. <strong>Almost all of this is proposal, '
        'not settled design</strong> &mdash; each group&rsquo;s notes in the repository say, per '
        'image, what the documents fix and what the render invents, and end with every guess '
        'in one list.</p></div>')

    out.write_text(head + '<div class="wrap">' + aside + '<main>' + lede
                   + "".join(sections) + '</main></div>',
                   encoding="utf-8", newline="\n")
    print(f"{out}  {out.stat().st_size/1e6:.1f} MB  {n_img} images  {n_con} concepts")


if __name__ == "__main__":
    main()
