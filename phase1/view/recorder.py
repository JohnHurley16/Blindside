"""Record a whole match to a video file, with the real mixer output as its sound.

Not part of the game. It exists so a match can be watched away from the machine that
ran it, and because the gate is a human watching for eight minutes -- which is easier
to arrange if the eight minutes can be replayed.

Audio is not a reconstruction: it is the same `Mixer` the live game uses, run in
offline mode and pulled one frame's worth at a time, so what is heard lines up with
what is on screen.
"""
from __future__ import annotations

import subprocess
import time
import wave
from pathlib import Path

import numpy as np

from .. import tuning as T
from ..audio.mixer import Mixer
from ..audio import voice as _voice
from ..match.match_view import MatchView
from .taught_rule import TaughtRule
from .view import View


class Recorder:
    def __init__(self, match: MatchView, out_path: str, fps: int = 20,
                 size: tuple[int, int] = (T.CANVAS_W, T.CANVAS_H), with_audio: bool = True,
                 reveal_seconds: float = 12.0, recall_at: float | None = None,
                 rule: TaughtRule | None = None) -> None:
        self.match: MatchView = match
        self.out_path: Path = Path(out_path)
        self.fps: int = fps
        self.size: tuple[int, int] = size
        self.reveal_seconds: float = reveal_seconds
        self.recall_at: float | None = recall_at
        self.mixer: Mixer | None = Mixer(offline=True) if with_audio else None
        self.view: View = View(match, audio=self.mixer, show=False, size=size, rule=rule)
        self.audio_chunks: list[np.ndarray] = []

    # ---- one frame ---------------------------------------------------------------------
    def _advance_to(self, target_t: float) -> None:
        if (self.recall_at is not None and self.match.t >= self.recall_at
                and not self.match.recall_used):
            self.match.recall()
        self.match.advance_to(target_t)

    def _frame(self) -> np.ndarray:
        """RGB with even dimensions.

        The canvas comes back larger than requested on a display with DPI scaling,
        and h264 in yuv420p cannot encode an odd width or height, so trim rather than
        trusting the requested size.
        """
        frame = self.view.canvas.render()[:, :, :3]
        h, w = frame.shape[:2]
        return frame[:h - (h % 2), :w - (w % 2)]

    def _pull_audio(self) -> None:
        if self.mixer is None:
            return
        self.audio_chunks.append(self.mixer.render_offline(1.0 / self.fps))

    def _orbit_for_reveal(self, progress: float) -> None:
        """Tilt off top-down during the reveal so the cloud reads as a 3D object and
        the fake wall height does something. Also makes belief and truth separate
        visually instead of overprinting each other."""
        camera = self.view.view.camera
        camera.elevation = 58.0 - 28.0 * progress
        camera.azimuth = 22.0 * progress

    # ---- the whole match ----------------------------------------------------------------
    def run(self) -> Path:
        import imageio.v2 as imageio

        cold_frames = int(T.COLD_OPEN_S * self.fps)
        total_frames = int((T.MATCH_SECONDS + self.reveal_seconds) * self.fps)
        video_path = self.out_path.with_suffix(".video.mp4")
        # Measured, per frame, at 1600x1000: readback 56 ms, draw 12, encode 12, sim 2.
        # The feasibility spike re-measured that and the attribution was wrong: readback
        # at 2000x1125 is 13.4 ms and the rest of render() is the draw. veryfast keeps
        # the encoder well clear of being the constraint, but it was never the
        # constraint; an earlier note here claiming the pipe backpressured was wrong.
        writer = imageio.get_writer(str(video_path), fps=self.fps, codec="libx264",
                                    quality=8, macro_block_size=1,
                                    ffmpeg_params=["-preset", "veryfast"])
        started = time.perf_counter()
        last_report = started
        try:
            # The cold open is prepended rather than run under the match, because the gate
            # viewer watched a recording: an explanation that only exists in the live
            # window is an explanation she never got. Six seconds at 20 fps, the sim held
            # at t = 0, the camera descending from 90 degrees to 72 underneath it.
            for frame_index in range(cold_frames):
                self.view.present_cold_open(frame_index / self.fps)
                self.view.draw()
                self._pull_audio()
                writer.append_data(self._frame())
            # Close it explicitly. The loop's last index is one frame short of
            # COLD_OPEN_S, so without this the card never reaches its own end: the
            # curtain stays down and the whole eight minutes record with the inset, the
            # minimap, the panel grounds and the timeline hidden.
            self.view.present_cold_open(T.COLD_OPEN_S)
            for frame_index in range(total_frames):
                t_target = frame_index / self.fps
                if t_target <= T.MATCH_SECONDS:
                    self._advance_to(t_target)
                else:
                    progress = min(1.0, (t_target - T.MATCH_SECONDS) / max(self.reveal_seconds, 1e-6))
                    self._orbit_for_reveal(progress)
                self.view.draw()
                self._pull_audio()
                writer.append_data(self._frame())
                if frame_index % (self.fps * 30) == 0:
                    # Rate over the last chunk, not since the beginning. A cumulative
                    # average never recovers from a slow start, and this line was
                    # reporting seventy-six minutes remaining on a render that had
                    # seven left.
                    now = time.perf_counter()
                    done = frame_index / total_frames
                    recent = now - last_report
                    rate = (self.fps * 30) / recent if recent > 0 else 0.0
                    eta = (total_frames - frame_index) / rate if rate > 0 else 0.0
                    last_report = now
                    elapsed = now - started
                    print(f"  {t_target:6.1f}s / {T.MATCH_SECONDS + self.reveal_seconds:.0f}s "
                          f"({done * 100:4.1f}%)  points {self.match.beliefs['player'].cloud.n:6d}"
                          f"  eta {eta / 60:.1f} min", flush=True)
        finally:
            writer.close()

        if self.mixer is None or not self.audio_chunks:
            video_path.replace(self.out_path)
            return self.out_path
        return self._mux(video_path)

    # ---- sound -----------------------------------------------------------------------------
    def _write_wav(self, path: Path) -> None:
        mix = np.concatenate(self.audio_chunks, axis=0)
        peak = float(np.max(np.abs(mix))) if mix.size else 0.0
        if peak > 0.0:
            mix = mix / max(peak, 1.0)          # only ever attenuate
        pcm = np.clip(mix, -1.0, 1.0)
        pcm = (pcm * 32767.0).astype(np.int16)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(_voice.SAMPLE_RATE)
            w.writeframes(pcm.tobytes())

    def _mux(self, video_path: Path) -> Path:
        import imageio_ffmpeg
        wav_path = self.out_path.with_suffix(".wav")
        self._write_wav(wav_path)
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
               "-i", str(video_path), "-i", str(wav_path),
               "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
               str(self.out_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("ffmpeg mux failed; keeping the silent video and the wav separately")
            print(result.stderr[-800:])
            video_path.replace(self.out_path)
            return self.out_path
        video_path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)
        return self.out_path
