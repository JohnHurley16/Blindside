"""Assemble VISION-BOARD.md and index.html from the six groups' NOTES.md.

Each group's notes carry concept sections (## or ### headings) holding markdown tables
whose rows name images in backticks with a one-line intent. This walks those, resolves
each basename against the group's tree, and writes the board and a contact sheet.

Run: python docs/art/vision/_assemble.py
"""
from __future__ import annotations

import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
GROUPS = [
    ("surface", "The surface",
     "The pit-head: the shaft, the yard, the training course, the descent, and the only sky in the game."),
    ("cave", "The descent and the cave",
     "Shaft, passages, chambers, water, silt, rock, depth, and the works the ancients left."),
    ("machinery", "The ancient machinery",
     "The Assayer dormant, winding and firing; its siblings; the download; a spent machine."),
    ("machines", "The machines",
     "Four chassis, loadouts in silhouette, teams, wear, damage, lamp, daylight."),
    ("found", "What is found, and the machine's own view",
     "Deposits, wrecks, beacons, discoveries; the point cloud as art; world against belief."),
    ("teaching", "Teaching, and the mood",
     "Where teaching happens, the interface in the world, palette strips per zone."),
]
PNG = re.compile(r"`([A-Za-z0-9_][A-Za-z0-9_.\-/]*\.png)`")
HEAD = re.compile(r"^(#{2,3})\s+(.*?)\s*$")
SKIP = ("every guess", "guesses", "design problems", "not done", "state of the board",
        "what the renders", "how the images", "how to re-render", "images",
        "the questions", "things this pass", "what this pass")


WEB = HERE / "web"
WEB_WIDTH = 900
WEB_QUALITY = 82
BROKEN: list[Path] = []


def web_copy(src: Path) -> str | None:
    """A committed 900 px JPEG beside the full-resolution render, so the board survives a
    clone: the PNGs are 157 MB and are gitignored, these are about 8 MB for the set.
    Returns the path relative to this directory, or None if the render is unreadable."""
    from PIL import Image

    rel = src.relative_to(HERE)
    dst = WEB / rel.with_suffix(".jpg")
    if dst.is_file() and dst.stat().st_mtime >= src.stat().st_mtime:
        return dst.relative_to(HERE).as_posix()
    try:
        im = Image.open(src)
        im.load()
        im = im.convert("RGB")
    except Exception:
        BROKEN.append(src)
        return None
    if im.width > WEB_WIDTH:
        im = im.resize((WEB_WIDTH, round(im.height * WEB_WIDTH / im.width)), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "JPEG", quality=WEB_QUALITY, optimize=True)
    return dst.relative_to(HERE).as_posix()


def index_images(group: str) -> list[Path]:
    """Every render in the group, concept directories before working directories, so a
    file copied into its concept folder wins over the raw frame it came from."""
    def rank(p: Path) -> tuple[int, str]:
        return (1 if any(s.startswith("_") for s in p.relative_to(HERE / group).parts) else 0,
                p.as_posix())
    return sorted((HERE / group).rglob("*.png"), key=rank)


def resolve(ref: str, images: list[Path], group: str, concept_dir: str | None) -> Path | None:
    """A note may name an image by bare name, by concept/name, or by the tail of a name
    that was rendered with a batch prefix (`01_clear_cutaway.png` -> `b1_01_clear_cutaway.png`)."""
    ref = ref.replace("\\", "/")
    tail = ref.rsplit("/", 1)[-1]
    pref = [p for p in images if concept_dir and p.parent.name == concept_dir]
    for pool in (pref, images):
        for p in pool:
            if p.relative_to(HERE / group).as_posix() == ref or p.name == tail:
                return p
    for pool in (pref, images):
        for p in pool:
            if p.name.endswith("_" + tail) or p.name.endswith(tail):
                return p
    return None


def parse(group: str) -> list[dict]:
    """Concepts, each with a title and its images in order of first mention."""
    notes = HERE / group / "NOTES.md"
    if not notes.is_file():
        return []
    images = index_images(group)
    dirs = {p.name for p in (HERE / group).iterdir() if p.is_dir()}
    concepts: list[dict] = []
    cur: dict | None = None
    seen: set[Path] = set()
    for line in notes.read_text(encoding="utf-8", errors="replace").splitlines():
        m = HEAD.match(line)
        if m:
            title = m.group(2).strip()
            if title.lower().startswith(SKIP):
                cur = None
                continue
            slug = title.split()[0].rstrip("/").strip("—-–")
            cur = {"title": title, "dir": slug if slug in dirs else None, "images": []}
            concepts.append(cur)
            continue
        refs = PNG.findall(line)
        if not refs or cur is None:
            continue
        if line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            body = [c for c in cells if not PNG.search(c)]
            intent = max(body, key=len) if body else ""
            label = " ".join(cells)
        else:
            intent = re.sub(r"^\s*[-*]\s*", "", line).strip()
            label = line
        for r in refs:
            p = resolve(r, images, group, cur["dir"])
            if p is None or p in seen:
                continue
            seen.add(p)
            cur["images"].append({"name": p.name, "path": p, "intent": intent,
                                  "kind": kind(label, p.name)})
    return [c for c in concepts if c["images"]]


def kind(label: str, name: str) -> str:
    """The notes say CLEAR or IN-SITU in the row; the filename is the fallback."""
    low = (label + " " + name).lower()
    if "in-situ" in low or "in situ" in low or "insitu" in low or "in_situ" in low:
        return "in situ"
    if "clear" in low or "daylight" in low or "ortho" in low or "plan" in low:
        return "clear"
    return ""


def main() -> None:
    board: list[str] = []
    cards: list[str] = []
    total = 0
    listed: set = set()
    rows: list[tuple[str, str, int, bool, bool]] = []

    board.append("# The vision board\n")
    board.append(
        "Every art concept in the game, surface and underground: at least one view that shows the\n"
        "thing and at least one in the game's own light. Rendered 2026-09-08. Open `index.html`\n"
        "beside this file to scroll the whole board as one contact sheet.\n")
    board.append(
        "**Most of this is proposal, not settled design.** Each group's `NOTES.md` says, per image,\n"
        "what it draws that the documents fix and what it invents, and ends with every guess in one\n"
        "list. Strike them there.\n")
    board.append("\n---\n")

    for key, title, blurb in GROUPS:
        concepts = parse(key)
        if not concepts:
            continue
        n = sum(len(c["images"]) for c in concepts)
        total += n
        board.append(f"\n## {title}\n")
        board.append(f"{blurb}\n")
        board.append(f"{n} images, {len(concepts)} concepts. Notes: [`{key}/NOTES.md`]({key}/NOTES.md)\n")
        cards.append(f'<h2 id="{key}">{html.escape(title)}</h2>'
                     f'<p class="blurb">{html.escape(blurb)}</p>')
        for c in concepts:
            kinds = {i["kind"] for i in c["images"]}
            rows.append((title, c["title"], len(c["images"]), "clear" in kinds, "in situ" in kinds))
            board.append(f"\n### {c['title']}\n")
            cards.append(f'<h3>{html.escape(c["title"])}</h3><div class="grid">')
            for im in c["images"]:
                rel = web_copy(im["path"])
                if rel is None:
                    continue
                listed.add(im["path"])
                full = im["path"].relative_to(HERE).as_posix()
                board.append(f"\n![{im['name']}]({rel})\n")
                board.append(f"*{im['intent'] or im['name']}*\n")
                k = im["kind"]
                tag = f'<span class="tag {k.replace(" ", "")}">{k}</span>' if k else ""
                cards.append(
                    f'<figure><a href="{full}" target="_blank">'
                    f'<img loading="lazy" src="{rel}" alt="{html.escape(im["name"])}"></a>'
                    f'<figcaption>{tag}<b>{html.escape(im["name"])}</b><br>'
                    f'{html.escape(im["intent"] or "")}</figcaption></figure>')
            cards.append("</div>")

    # Renders the notes do not list: intermediates and frames that never got a caption.
    # They are counted here rather than dropped silently.
    unlisted: list[tuple[str, int]] = []
    for key, title, _ in GROUPS:
        n = sum(1 for p in (HERE / key).rglob("*.png") if p not in listed)
        if n:
            unlisted.append((title, n))
    if unlisted:
        board.append("\n---\n")
        board.append("\n## Renders the notes do not caption\n")
        board.append(
            "Intermediates and extra frames that no concept table names. They are on disk under\n"
            "each group's directory and are not in the board above.\n")
        for t, n in unlisted:
            board.append(f"\n- {t}: {n}")
        board.append("\n")

    both = sum(1 for r in rows if r[3] and r[4])
    missing = [(g, c) for g, c, _, cl, ins in rows if not (cl and ins)]
    board.insert(4, f"\n{total} images, {len(rows)} concepts. "
                    f"{both} have both a clear and an in-situ view; "
                    f"{len(missing)} have only one. "
                    f"{sum(n for _, n in unlisted)} further renders are uncaptioned.\n")
    if missing:
        board.append("\n## Concepts with only one kind of view\n")
        for g, c in missing:
            board.append(f"\n- {g} — {c}")
        board.append("\n")
    (HERE / "VISION-BOARD.md").write_text("\n".join(board), encoding="utf-8", newline="\n")

    nav = " ".join(f'<a href="#{k}">{html.escape(t)}</a>' for k, t, _ in GROUPS)
    style = """
:root { color-scheme: dark; }
body { margin:0; background:#0d0c0b; color:#d8d2c8; font:14px/1.5 system-ui,sans-serif; }
header { position:sticky; top:0; background:#0d0c0bee; padding:12px 20px;
         border-bottom:1px solid #2a2724; z-index:9; }
header b { color:#f0e9dd; letter-spacing:.06em; }
nav a { color:#b99b6a; margin-right:14px; text-decoration:none; font-size:13px; }
nav a:hover { text-decoration:underline; }
main { padding:0 20px 80px; max-width:1900px; }
h2 { margin:44px 0 4px; font-size:22px; color:#f0e9dd;
     border-bottom:1px solid #2a2724; padding-bottom:6px; }
h3 { margin:26px 0 10px; font-size:15px; color:#b99b6a; font-weight:600; }
.blurb { margin:0 0 8px; color:#8d857a; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); gap:16px; }
figure { margin:0; background:#141210; border:1px solid #262220; border-radius:3px;
         overflow:hidden; }
figure img { width:100%; display:block; background:#000; }
figcaption { padding:8px 10px; font-size:12px; color:#9e968a; }
figcaption b { color:#cfc7b9; font-weight:600; }
.tag { display:inline-block; font-size:10px; text-transform:uppercase; letter-spacing:.08em;
       padding:1px 6px; border-radius:2px; margin-right:6px; vertical-align:1px; }
.tag.clear { background:#2b3a46; color:#9fc4dd; }
.tag.insitu { background:#3a2c20; color:#d0a06a; }
"""
    head = (f'<!doctype html><meta charset="utf-8">'
            f'<title>BLINDSIDE - vision board</title><style>{style}</style>'
            f'<header><b>BLINDSIDE &mdash; vision board</b> &nbsp; '
            f'<span style="color:#8d857a">{total} images, {len(rows)} concepts, '
            f'{both} with both a clear and an in-situ view</span><br><nav>{nav}</nav></header>')
    (HERE / "index.html").write_text(head + "<main>" + "".join(cards) + "</main>\n",
                                     encoding="utf-8", newline="\n")

    print(f"images {total}  concepts {len(rows)}  both views {both}")
    for g, c, n, cl, ins in rows:
        if not (cl and ins):
            print(f"  MISSING {'clear' if not cl else 'in-situ'}: {g} / {c} ({n} images)")


if __name__ == "__main__":
    main()
