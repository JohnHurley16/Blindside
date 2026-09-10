"""Assemble the trailer from the shot sequences the spikes have rendered.

Finds every image sequence across the Godot spikes, orders them by the shot list in
docs/TRAILER.md, and cuts them together with the text cards. Uses the ffmpeg that ships
inside imageio_ffmpeg, so nothing has to be installed.

    python spikes/godot/_assemble_cut.py OUT.mp4 [--fps 24] [--hold 1.0]

--hold is seconds per shot. The spikes currently render 24 frames per shot, so a hold of
1.0 plays them at native speed and anything longer stretches them; the treatment's real
durations need longer renders, which is a separate job.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# (sequence directory relative to spikes/godot, card text shown after this shot or None)
# Order follows docs/TRAILER.md section 3. Missing entries are skipped and reported.
SHOTS: list[tuple[str, str, str | None]] = [
    ("surface/shots/cinema/seq/t02_headframe_sky", "2", None),
    ("surface/shots/cinema/seq/t03_yard_drift", "3", None),
    ("surface/shots/cinema/seq/t04_rain_macro", "4", None),
    ("surface/shots/cinema/seq/t05_charge_line", "5", None),
    ("surface/shots/cinema/seq/t06_bench_machine", "6", "Nothing down there answers to you."),
    ("surface/shots/cinema/seq/t07_course_posts", "7", None),
    ("surface/shots/cinema/seq/t12_course_alone", "12", "You cannot drive it.\nYou can only teach it."),
    ("surface/shots/cinema/seq/t13_collar_above", "13", None),
    ("cave/shots/cinema/seq/t16_lamp_comes_on", "16", "Twenty seconds after it goes down,\nit stops listening."),
    ("cave/shots/cinema/seq/t17_follow_machine", "17", None),
    ("cloud/shots/cinema/seq/t18_belief_cut", "18", "It only knows what it has seen."),
    ("cloud/shots/cinema/seq/t19_cloud_building", "19", None),
    ("cloud/shots/cinema/seq/t20_sensor_shadow", "20", None),
    ("cave/shots/cinema/seq/t20_sensor_shadow", "20c", None),
    ("cloud/shots/cinema/seq/t21_both_registers", "21", None),
    ("assayer/shots/seq/s23_mast_in_the_dark", "23", None),
    ("assayer/shots/seq/s24a_the_slew", "24a", None),
    ("assayer/shots/seq/s24b_the_wind", "24b", None),
    ("assayer/shots/seq/s25_the_strike", "25", None),
    ("cloud/shots/cinema/seq/t26_the_fold", "26", "And it can be lied to."),
    ("cave/shots/cinema/seq/t27_wrong_direction", "27", None),
    ("surface/shots/cinema/seq/t28_extraction_window", "28", None),
]

W, H = 1920, 1080


def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def frames(d: Path) -> list[Path]:
    return sorted(p for p in d.glob("*.png"))


def card_filter(text: str, dur: float) -> list[str]:
    """A black card with the line centred, faded in and out."""
    esc = text.replace("\\", r"\\").replace(":", r"\:").replace("'", r"\'")
    lines = esc.split("\n")
    draws = []
    for i, ln in enumerate(lines):
        y = f"(h-text_h)/2+{(i - (len(lines) - 1) / 2) * 64:.0f}"
        draws.append(
            f"drawtext=text='{ln}':fontcolor=0xE9E0D2:fontsize=46:x=(w-text_w)/2:y={y}"
            f":alpha='if(lt(t,0.4),t/0.4,if(lt(t,{dur - 0.5:.2f}),1,max(0,({dur:.2f}-t)/0.5)))'")
    return draws


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--hold", type=float, default=1.0, help="seconds per shot")
    ap.add_argument("--card", type=float, default=2.0, help="seconds per text card")
    a = ap.parse_args()

    exe = ffmpeg()
    tmp = Path(tempfile.mkdtemp(prefix="cut_"))
    parts: list[Path] = []
    missing: list[str] = []

    try:
        for rel, tag, card in SHOTS:
            d = ROOT / rel
            fs = frames(d) if d.is_dir() else []
            if not fs:
                missing.append(f"{tag}  {rel}")
                continue
            # one clip per shot, stretched or compressed to --hold
            src = tmp / f"src_{tag}"
            src.mkdir()
            for i, f in enumerate(fs):
                shutil.copy(f, src / f"{i:04d}.png")
            clip = tmp / f"{len(parts):03d}_{tag}.mp4"
            in_fps = len(fs) / a.hold
            subprocess.run(
                [exe, "-y", "-loglevel", "error", "-framerate", f"{in_fps:.4f}",
                 "-i", str(src / "%04d.png"),
                 "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,fps={a.fps},format=yuv420p",
                 "-c:v", "libx264", "-preset", "medium", "-crf", "17", str(clip)],
                check=True)
            parts.append(clip)

            if card:
                cd = tmp / f"{len(parts):03d}_card.mp4"
                subprocess.run(
                    [exe, "-y", "-loglevel", "error", "-f", "lavfi",
                     "-i", f"color=c=black:s={W}x{H}:d={a.card}:r={a.fps}",
                     "-vf", ",".join(card_filter(card, a.card)) + ",format=yuv420p",
                     "-c:v", "libx264", "-preset", "medium", "-crf", "17", str(cd)],
                    check=True)
                parts.append(cd)

        # title
        title = tmp / "zzz_title.mp4"
        subprocess.run(
            [exe, "-y", "-loglevel", "error", "-f", "lavfi",
             "-i", f"color=c=black:s={W}x{H}:d=4:r={a.fps}",
             "-vf", "drawtext=text='BLINDSIDE':fontcolor=0xE9E0D2:fontsize=96:"
                    "x=(w-text_w)/2:y=(h-text_h)/2-20:"
                    "alpha='if(lt(t,0.8),t/0.8,1)',"
                    "drawtext=text='in development':fontcolor=0x9A9084:fontsize=30:"
                    "x=(w-text_w)/2:y=(h-text_h)/2+70:"
                    "alpha='if(lt(t,1.6),max(0\\,(t-1.0)/0.6),1)',format=yuv420p",
             "-c:v", "libx264", "-preset", "medium", "-crf", "17", str(title)],
            check=True)
        parts.append(title)

        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
        out = Path(a.out)
        subprocess.run([exe, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c", "copy", str(out)], check=True)

        dur = subprocess.run(
            [exe, "-i", str(out)], capture_output=True, text=True).stderr
        secs = [l for l in dur.splitlines() if "Duration" in l]
        print(f"wrote {out}  ({out.stat().st_size/1e6:.1f} MB)")
        if secs:
            print(secs[0].strip())
        print(f"{len(parts)} segments from {len(SHOTS) - len(missing)} shots")
        if missing:
            print(f"MISSING {len(missing)} shots, not silently skipped:")
            for m in missing:
                print("  " + m)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
