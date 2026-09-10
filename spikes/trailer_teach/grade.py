"""Frame, warp and grade the raw teach-window renders into trailer shots.

TRAILER.md section 7 says how the teaching act has to be handled: the teach panel is
a 2D Python view, so it is "shot over the shoulder at an angle, treated as a screen
in the world rather than as the game's UI". That is what this file does, and it is a
composite rather than a photograph: the screen content is captured from something
that runs (capture.py, frame by frame, on a fixed clock), but the room around it, the
bezel and the operator's shoulder are drawn here. They are the only invented pixels
in the shot and they are listed as such in NOTES.md.

Order, and every step is something a lens or a sensor does in this light:

  1  crop and move       the shot's framing, eased, with handheld on the handheld ones
  2  screen structure    pixel pitch and the display's own glare, at the screen's scale
  3  perspective         the screen as a quad, seen from the operator's left
  4  the room            near-black warm, lit only by the screen; bezel; spill
  4b the glass           the room's own warm veiling reflection in the screen's face
  5  the shoulder        a defocused foreground body, rim-lit by the screen
  6  the lens            veiling glare, barrel, chromatic aberration at the edge
  7  the sensor          vignette, grain in the shadows, black point on the cave's

The grade target is the cave spike's own frames, measured: black floor at 3/255,
warm darks around R11 G8 B6. The screen itself is left cold -- ART-DIRECTION's two
registers are the world warm and belief cold, and a display in a dark room is the one
place they are allowed in the same frame.
"""
from __future__ import annotations

import argparse
import math
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
SEQ = HERE / "seq"
W, H = 1920, 1080

# ---- the shots ---------------------------------------------------------------------------------
# `start` and `end` are crop boxes in the raw render's own pixels: the framing move.
#
# `fill` is the screen's width as a multiple of the frame's; `right` and `bottom` are
# where the screen's right and bottom edges land, so a shot whose crop runs to the
# canvas edge can show a real screen edge with the room beyond it, and a shot cropped
# into the middle of the canvas overfills instead -- a frame that cuts through the
# panel is the camera being tight, not the UI being broken. Shot 10 deliberately puts
# its right edge just outside the frame: `because:` does not wrap and clips at the
# canvas edge for those three stops (see NOTES.md 6), and a word cut by the frame
# reads as a tight shot where the same word cut by a visible bezel reads as a bug.
#
# The shoulder is in the master (8) and the rule (11) and out of the rest: in 9, 10
# and 12 the line that carries the shot -- `you chose: go back`, `it is driving
# itself` -- is the footer, bottom left, which is exactly where a foreground body
# goes. A tighter insert without the operator in it is ordinary coverage; losing the
# words is not.
SHOTS = {
    "08_panel_stopped": dict(
        frames=120,
        start=(0, 0, 3840, 2160),
        end=(330, 120, 3510, 1974),
        handheld=True, keystone=0.05, tilt=-1.1, fill=1.06, right=1858, bottom=1150,
        shoulder=True,
        note="the panel, stopped, four things it could do",
    ),
    "09_choice_taken": dict(
        frames=72,
        start=(40, 560, 2760, 1552),
        end=(0, 574, 2820, 1586),
        handheld=True, keystone=0.04, tilt=-0.8, fill=1.00, right=1958, bottom=1052,
        shoulder=False,
        note="a choice is taken and it moves",
    ),
    "10_three_stops": dict(
        frames=96,
        # Each beat is tighter than the last and every one keeps its right edge on the
        # canvas edge, because the rail has to reach the frame edge; the punch-in is
        # therefore taken off the left and the top, and by the third beat the clock and
        # the header are gone and only the question is left.
        beats=((0, 32, (210, 60, 3630, 2042), (250, 84, 3590, 2019)),
               (32, 32, (440, 200, 3400, 1913), (480, 224, 3360, 1890)),
               (64, 32, (670, 350, 3170, 1783), (710, 374, 3130, 1761))),
        handheld=True, keystone=0.045, tilt=-1.5, fill=1.05, right=1934, bottom=1128,
        shoulder=False,
        note="three stops, three beliefs, three answers",
    ),
    "11_the_rule": dict(
        frames=96,
        start=(5888, 2589, 2112, 1188),
        end=(6080, 2643, 1920, 1080),
        handheld=False, keystone=0.038, tilt=-0.7, fill=1.06, right=1862, bottom=1140,
        shoulder=True,
        note="the rule in its own words, lighting the branch it took",
    ),
    "12_runs_alone": dict(
        frames=96,
        start=(0, 640, 2700, 1519),
        end=(40, 652, 2640, 1485),
        handheld=False, keystone=0.04, tilt=-0.9, fill=1.00, right=1950, bottom=1056,
        shoulder=False,
        note="it walks on with nobody touching anything",
    ),
}


def smoothstep(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def lerp_box(a, b, u):
    return tuple(av + (bv - av) * u for av, bv in zip(a, b))


# ---- 3: the screen as a quad --------------------------------------------------------------------
def perspective_coeffs(dst, src):
    """PIL maps an output pixel back into the input, so solve dst -> src."""
    matrix = []
    for (dx, dy), (sx, sy) in zip(dst, src):
        matrix.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy])
        matrix.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy])
    A = np.array(matrix, dtype=np.float64)
    B = np.array([c for pt in src for c in pt], dtype=np.float64)
    return np.linalg.solve(A, B)


def screen_quad(keystone: float, tilt_deg: float, fill: float, right: float,
                bottom: float, wobble):
    """Where the four corners of the screen land in the frame.

    Over the operator's left shoulder: the screen's far (right) edge is shorter than
    its near (left) edge, and the whole panel is tipped a degree or so off level. The
    right and bottom edges are placed; the left and top fall where they fall, off the
    frame when the screen is bigger than it.
    """
    hw, hh = W * fill / 2.0, H * fill / 2.0
    cx, cy = right - hw, bottom - hh
    near, far = 1.0, 1.0 - keystone
    pts = [(-hw, -hh * near), (hw, -hh * far), (hw, hh * far), (-hw, hh * near)]
    a = math.radians(tilt_deg)
    ca, sa = math.cos(a), math.sin(a)
    dx, dy, dr = wobble
    a2 = math.radians(dr)
    ca2, sa2 = math.cos(a2), math.sin(a2)
    out = []
    for x, y in pts:
        x, y = x * ca - y * sa, x * sa + y * ca
        x, y = x * ca2 - y * sa2, x * sa2 + y * ca2
        out.append((cx + x + dx, cy + y + dy))
    return out


def handheld(frame: int, on: bool):
    """Low frequency, sub-degree, and it never repeats inside a shot."""
    if not on:
        return (0.0, 0.0, 0.0)
    t = frame / 24.0
    dx = 2.6 * math.sin(t * 1.07 + 0.4) + 1.3 * math.sin(t * 2.31 + 1.9)
    dy = 2.1 * math.sin(t * 0.83 + 2.2) + 1.1 * math.sin(t * 1.97 + 0.6)
    dr = 0.10 * math.sin(t * 0.61 + 1.1) + 0.05 * math.sin(t * 1.43)
    return (dx, dy, dr)


# ---- 2: what a display does ---------------------------------------------------------------------
def screen_structure(panel: Image.Image) -> Image.Image:
    """Pixel pitch and the display's own glare, applied at the screen's scale so the
    grid is the screen's rather than the frame's."""
    a = np.asarray(panel, dtype=np.float32)
    h, w = a.shape[:2]
    rows = (np.arange(h) % 3 == 0).astype(np.float32)[:, None, None]
    a *= 1.0 - 0.035 * rows
    cols = (np.arange(w) % 3 == 0).astype(np.float32)[None, :, None]
    a *= 1.0 - 0.020 * cols
    bright = np.clip((a.max(2) - 150.0) / 105.0, 0.0, 1.0)
    glare = Image.fromarray((bright * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(6))
    g = np.asarray(glare, dtype=np.float32)[:, :, None] / 255.0
    a += g * np.array([120.0, 150.0, 170.0], dtype=np.float32) * 0.5
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ---- 4, 5: the room and the body in front of it --------------------------------------------------
def room_base() -> np.ndarray:
    """Near-black, warm, unlit except by the screen. Measured off the cave spike:
    darks sit around R11 G8 B6 with the floor at 3."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    fall = np.exp(-((x - W * 0.42) ** 2) / (2 * (W * 0.85) ** 2)
                  - ((y - H * 0.30) ** 2) / (2 * (H * 0.9) ** 2))
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:, :, 0] = 3.0 + 9.0 * fall
    base[:, :, 1] = 3.0 + 6.6 * fall
    base[:, :, 2] = 3.0 + 4.8 * fall
    return base


def shoulder_mask() -> tuple[np.ndarray, np.ndarray]:
    """A body in the bottom-left, out of focus, and the edge the screen rim-lights."""
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    d.polygon([(-300, H + 200), (-300, int(H * 0.72)), (int(W * 0.035), int(H * 0.62)),
               (int(W * 0.115), int(H * 0.66)), (int(W * 0.175), int(H * 0.80)),
               (int(W * 0.205), H + 200)], fill=255)
    body = m.filter(ImageFilter.GaussianBlur(34))
    inner = m.filter(ImageFilter.GaussianBlur(10)).point(lambda v: 255 if v > 200 else 0)
    rim = Image.fromarray(
        np.clip(np.asarray(body, dtype=np.float32) - np.asarray(inner, dtype=np.float32),
                0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9))
    return (np.asarray(body, dtype=np.float32) / 255.0,
            np.asarray(rim, dtype=np.float32) / 255.0)


# ---- 6, 7: the lens and the sensor ---------------------------------------------------------------
def barrel(a: np.ndarray, k: float = 0.004) -> np.ndarray:
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (x - W / 2) / (W / 2)
    ny = (y - H / 2) / (H / 2)
    r2 = nx * nx + ny * ny
    f = 1.0 + k * r2
    sx = np.clip((nx * f * (W / 2) + W / 2), 0, W - 1).astype(np.int32)
    sy = np.clip((ny * f * (H / 2) + H / 2), 0, H - 1).astype(np.int32)
    return a[sy, sx]


def aberration(a: np.ndarray, px: float = 0.85) -> np.ndarray:
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (x - W / 2) / (W / 2)
    ny = (y - H / 2) / (H / 2)
    r2 = nx * nx + ny * ny
    out = a.copy()
    for channel, sign in ((0, 1.0), (2, -1.0)):
        f = 1.0 + sign * px * r2 / (W / 2)
        sx = np.clip(nx * f * (W / 2) + W / 2, 0, W - 1).astype(np.int32)
        sy = np.clip(ny * f * (H / 2) + H / 2, 0, H - 1).astype(np.int32)
        out[:, :, channel] = a[sy, sx, channel]
    return out


def big_blur(img: Image.Image, radius: float, step: int = 4) -> Image.Image:
    """A wide blur costs nothing at a quarter scale and looks the same: the only use
    here is spill and veiling glare, neither of which has any detail in it."""
    small = img.resize((W // step, H // step), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(radius / step))
    return small.resize((W, H), Image.BILINEAR)


REFLECTION = None


def reflection() -> np.ndarray:
    """What the room puts back into the glass.

    The screen is cold and the rest of the trailer is warm iron. Measured against
    `cave/shots/cinema/seq/`, a graded panel with no reflection lands on the cave's
    black floor and its exposure but keeps a blue cast through 90 per cent of the
    frame, because 90 per cent of the frame is screen. A real display in a lamp-lit
    room does not: its face carries a dim warm veiling reflection of the room, which
    is the physical reason a photographed monitor never looks as blue as the signal
    going into it. Broad, dim, brightest where a lamp would be, and it goes nowhere
    near the highlights."""
    global REFLECTION
    if REFLECTION is None:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        lamp = np.exp(-((x - W * 0.24) ** 2) / (2 * (W * 0.62) ** 2)
                      - ((y - H * 0.10) ** 2) / (2 * (H * 0.78) ** 2))
        REFLECTION = (np.stack([1.4 + 6.5 * lamp, 1.0 + 4.6 * lamp, 0.6 + 2.9 * lamp], 2)
                      .astype(np.float32))
    return REFLECTION


VIGNETTE = None


def vignette() -> np.ndarray:
    global VIGNETTE
    if VIGNETTE is None:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        nx = (x - W * 0.5) / (W * 0.5)
        ny = (y - H * 0.5) / (H * 0.5)
        r = np.sqrt(nx * nx + ny * ny) / math.sqrt(2)
        VIGNETTE = (1.0 - 0.42 * r ** 2.2)[:, :, None]
    return VIGNETTE


def grain(a: np.ndarray, frame: int) -> np.ndarray:
    rng = np.random.default_rng(1000 + frame)
    n = rng.normal(0.0, 1.0, (H, W, 1)).astype(np.float32)
    shadow = np.clip(1.0 - a.mean(2, keepdims=True) / 90.0, 0.15, 1.0)
    return a + n * 3.4 * shadow


# ---- one frame ------------------------------------------------------------------------------------
class Grader:
    def __init__(self) -> None:
        self.base = room_base()
        self.body, self.rim = shoulder_mask()

    def frame(self, raw: Image.Image, box, spec, index: int) -> Image.Image:
        x, y, w, h = (int(round(v)) for v in box)
        panel = raw.crop((x, y, x + w, y + h)).resize((W, H), Image.LANCZOS)
        panel = screen_structure(panel)

        dst = screen_quad(spec["keystone"], spec["tilt"], spec["fill"],
                          spec["right"], spec["bottom"],
                          handheld(index, spec["handheld"]))
        src = [(0, 0), (W, 0), (W, H), (0, H)]
        coeffs = perspective_coeffs(dst, src)
        warped = panel.transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
        mask = Image.new("L", (W, H), 255).transform(
            (W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC)

        screen = np.asarray(warped, dtype=np.float32)
        m = (np.asarray(mask.filter(ImageFilter.GaussianBlur(1.2)),
                        dtype=np.float32) / 255.0)[:, :, None]

        # the bezel: the same quad, a little larger, in dark warm metal
        qx = sum(p[0] for p in dst) / 4.0
        qy = sum(p[1] for p in dst) / 4.0
        bezel_dst = [(px + (px - qx) * 0.024, py + (py - qy) * 0.024) for px, py in dst]
        bmask = Image.new("L", (W, H), 255).transform(
            (W, H), Image.PERSPECTIVE, perspective_coeffs(bezel_dst, src), Image.BICUBIC)
        bm = (np.asarray(bmask.filter(ImageFilter.GaussianBlur(2.0)),
                         dtype=np.float32) / 255.0)[:, :, None]

        # the room, lit by the screen and nothing else
        spill_src = Image.fromarray(np.clip(screen * m, 0, 255).astype(np.uint8))
        spill = np.asarray(big_blur(spill_src, 110.0), dtype=np.float32)
        out = self.base + spill * np.array([0.16, 0.20, 0.26], dtype=np.float32)
        edge = np.clip(np.asarray(
            bmask.filter(ImageFilter.GaussianBlur(3.0)), dtype=np.float32) / 255.0
            - np.asarray(mask, dtype=np.float32) / 255.0, 0.0, 1.0)[:, :, None]
        out = out * (1.0 - bm) + (out * 0.5 + np.array([14.0, 11.5, 9.0])) * bm
        out += edge * np.array([26.0, 24.0, 22.0], dtype=np.float32)
        out = out * (1.0 - m) + (screen + reflection()) * m

        # the operator, in front of it and out of focus
        if spec["shoulder"]:
            body = self.body[:, :, None]
            rim = self.rim[:, :, None]
            out = out * (1.0 - body * 0.955)
            out += rim * np.array([34.0, 42.0, 54.0], dtype=np.float32) * body

        # the lens: veiling glare off a bright source in a dark room
        veil = np.asarray(big_blur(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)),
                                   70.0), dtype=np.float32)
        out = out + veil * 0.055
        out = barrel(out)
        out = aberration(out)

        # the sensor
        out = out * vignette()
        out = grain(out, index)
        out = np.clip(out, 0.0, 255.0)
        out = 3.0 + out * (252.0 / 255.0)          # the cave spike's black floor
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def boxes_for(spec, frames):
    """The framing move, frame by frame, eased in and out."""
    if "beats" in spec:
        out = [None] * frames
        for at, count, start, end in spec["beats"]:
            for i in range(count):
                out[at + i] = lerp_box(start, end, smoothstep(i / max(count - 1, 1)))
        return out
    return [lerp_box(spec["start"], spec["end"], smoothstep(i / max(frames - 1, 1)))
            for i in range(frames)]


def run(name: str) -> None:
    spec = SHOTS[name]
    src = RAW / name
    out = SEQ / name
    out.mkdir(parents=True, exist_ok=True)
    frames = spec["frames"]
    boxes = boxes_for(spec, frames)
    grader = Grader()
    started = time.perf_counter()
    for i in range(frames):
        raw = Image.open(src / f"{i:03d}.png").convert("RGB")
        grader.frame(raw, boxes[i], spec, i).save(out / f"{i:03d}.png", compress_level=4)
    print(f"{name}: {frames} frames -> {out} "
          f"({(time.perf_counter() - started) / frames * 1000:.0f} ms/frame)  {spec['note']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("shot", nargs="?", default="all")
    args = ap.parse_args()
    names = list(SHOTS) if args.shot == "all" else [args.shot]
    for name in names:
        run(name)


if __name__ == "__main__":
    main()
