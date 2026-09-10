"""Assemble the trailer from the shot sequences the spikes have rendered.

Cuts every sequence together in the order of docs/TRAILER.md section 3, adds the text cards
and the title, and lays the score under it. Uses the ffmpeg inside imageio_ffmpeg, so nothing
has to be installed.

    python spikes/godot/_assemble_cut.py OUT.mp4 [--fps 24] [--no-audio]

Each sequence plays at its rendered length: the spikes render at 24 fps, so a 120-frame shot
is five seconds. A shot whose sequence is missing is reported, never silently skipped.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
SCORE = REPO / "spikes" / "score" / "trailer-score.wav"

# (sequence directory, tag, card shown after this shot or None)
# Order and cards follow docs/TRAILER.md sections 3 and 4.
SHOTS: list[tuple[str, str, str | None]] = [
    # Act I - the place
    ("surface/shots/cinema/seq/t02_valley_first_light", "02", None),
    ("surface/shots/cinema/seq/t03_yard_under_the_wall", "03", None),
    ("surface/shots/cinema/seq/t04_melt_macro", "04", None),
    ("surface/shots/cinema/seq/t05_charge_line", "05", None),
    ("surface/shots/cinema/seq/t06_meet_the_machine", "06", "Nothing down there answers to you."),
    # Act II - the teaching
    ("surface/shots/cinema/seq/t07_course_posts", "07", None),
    ("../trailer_teach/seq/08_panel_stopped", "08", None),
    ("../trailer_teach/seq/09_choice_taken", "09", None),
    ("../trailer_teach/seq/10_three_stops", "10", None),
    ("../trailer_teach/seq/11_the_rule", "11", None),
    ("surface/shots/cinema/seq/t12_course_alone", "12",
     "You cannot drive it.\nYou can only teach it."),
    # Act III - the commit
    ("surface/shots/cinema/seq/t13_collar_above", "13", None),
    ("surface/shots/cinema/seq/t14_descending", "14",
     "Twenty seconds after it goes down,\nit stops listening."),
    # Act IV - the dark
    ("cave/shots/cinema/seq/t16_lamp_comes_on", "16", None),
    ("cave/shots/cinema/seq/t17_follow_machine", "17", None),
    ("cloud/shots/cinema/seq/t18_belief_cut", "18", "It only knows what it has seen."),
    ("cloud/shots/cinema/seq/t19_cloud_building", "19", None),
    ("cloud/shots/cinema/seq/t20_sensor_shadow", "20", None),
    ("cloud/shots/cinema/seq/t21_two_registers", "21", None),
    # Act V - what is down there
    ("assayer/shots/seq/s23_mast_in_the_dark", "23", None),
    ("assayer/shots/seq/s24a_the_slew", "24a", None),
    ("assayer/shots/seq/s24b_the_wind", "24b", None),
    ("assayer/shots/seq/s25_the_strike", "25", None),
    ("cloud/shots/cinema/seq/t26_the_fold", "26", "And it can be lied to."),
    ("cave/shots/cinema/seq/t27_wrong_direction", "27", None),
    # Act VI
    ("surface/shots/cinema/seq/t28_extraction_window", "28", None),
]

W, H = 1920, 1080
CARD_S = 2.4


def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def card_filter(text: str, dur: float) -> str:
    esc = text.replace("\\", r"\\").replace(":", r"\:").replace("'", r"\'")
    lines = esc.split("\n")
    draws = []
    for i, ln in enumerate(lines):
        y = f"(h-text_h)/2+{(i - (len(lines) - 1) / 2) * 64:.0f}"
        draws.append(
            f"drawtext=text='{ln}':fontcolor=0xE9E0D2:fontsize=46:x=(w-text_w)/2:y={y}"
            f":alpha='if(lt(t,0.5),t/0.5,if(lt(t,{dur - 0.6:.2f}),1,max(0,({dur:.2f}-t)/0.6)))'")
    return ",".join(draws)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--no-audio", action="store_true")
    a = ap.parse_args()

    exe = ffmpeg()
    tmp = Path(tempfile.mkdtemp(prefix="cut_"))
    parts: list[Path] = []
    missing: list[str] = []
    total_frames = 0

    try:
        for rel, tag, card in SHOTS:
            d = (ROOT / rel).resolve()
            fs = sorted(d.glob("*.png")) if d.is_dir() else []
            if not fs:
                missing.append(f"{tag:4} {rel}")
                continue
            src = tmp / f"src_{tag}"
            src.mkdir()
            for i, f in enumerate(fs):
                shutil.copy(f, src / f"{i:04d}.png")
            clip = tmp / f"{len(parts):03d}_{tag}.mp4"
            subprocess.run(
                [exe, "-y", "-loglevel", "error", "-framerate", str(a.fps),
                 "-i", str(src / "%04d.png"),
                 "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,format=yuv420p",
                 "-c:v", "libx264", "-preset", "medium", "-crf", "17", str(clip)],
                check=True)
            parts.append(clip)
            total_frames += len(fs)

            if card:
                cd = tmp / f"{len(parts):03d}_card.mp4"
                subprocess.run(
                    [exe, "-y", "-loglevel", "error", "-f", "lavfi",
                     "-i", f"color=c=black:s={W}x{H}:d={CARD_S}:r={a.fps}",
                     "-vf", card_filter(card, CARD_S) + ",format=yuv420p",
                     "-c:v", "libx264", "-preset", "medium", "-crf", "17", str(cd)],
                    check=True)
                parts.append(cd)
                total_frames += int(CARD_S * a.fps)

        title = tmp / "zzz_title.mp4"
        subprocess.run(
            [exe, "-y", "-loglevel", "error", "-f", "lavfi",
             "-i", f"color=c=black:s={W}x{H}:d=5:r={a.fps}",
             "-vf", "drawtext=text='BLINDSIDE':fontcolor=0xE9E0D2:fontsize=104:"
                    "x=(w-text_w)/2:y=(h-text_h)/2-24:"
                    "alpha='if(lt(t,1.0),t/1.0,1)',"
                    "drawtext=text='in development':fontcolor=0x9A9084:fontsize=30:"
                    "x=(w-text_w)/2:y=(h-text_h)/2+80:"
                    "alpha='if(lt(t,2.0),max(0\\,(t-1.2)/0.8),1)',format=yuv420p",
             "-c:v", "libx264", "-preset", "medium", "-crf", "17", str(title)],
            check=True)
        parts.append(title)
        total_frames += 5 * a.fps

        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
        silent = tmp / "silent.mp4"
        subprocess.run([exe, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c", "copy", str(silent)], check=True)

        out = Path(a.out)
        if a.no_audio or not SCORE.is_file():
            shutil.copy(silent, out)
            if not SCORE.is_file() and not a.no_audio:
                print(f"NO SCORE at {SCORE} - cut is silent. Render it with:")
                print("  python -m phase1.audio.score_render")
        else:
            subprocess.run(
                [exe, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(SCORE),
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)],
                check=True)

        secs = total_frames / a.fps
        print(f"wrote {out}  ({out.stat().st_size/1e6:.1f} MB)  "
              f"{total_frames} frames = {int(secs//60)}:{secs%60:04.1f}")
        print(f"{len(parts)} segments from {len(SHOTS) - len(missing)} of {len(SHOTS)} shots")
        if missing:
            print(f"MISSING {len(missing)}, reported rather than skipped:")
            for m in missing:
                print("  " + m)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
