from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg

from config import settings
from store import save_frame_times, snapshot_dir


def _ffmpeg_bin() -> str:
    system = shutil.which("ffmpeg")
    if system:
        return system
    return imageio_ffmpeg.get_ffmpeg_exe()


def extract_frames(video_path: str | Path, camera_id: str, fps: float = 1.0) -> int:
    video = Path(video_path)
    if not video.is_file():
        raise FileNotFoundError(f"Video not found: {video}")

    out_dir = snapshot_dir(camera_id)
    for old in out_dir.glob("*.jpg"):
        old.unlink()

    dest = out_dir / "frame_%04d.jpg"
    cmd = [
        _ffmpeg_bin(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video),
        "-vf",
        f"fps={fps}",
        str(dest),
    ]
    subprocess.run(cmd, check=True)
    frames = sorted(out_dir.glob("frame_*.jpg"))
    keep = max(2, settings.snapshot_keep_file_frames)
    indexed = [(path, round(i / max(fps, 0.001), 3)) for i, path in enumerate(frames)]
    if len(indexed) > keep:
        chosen = {round(i * (len(indexed) - 1) / (keep - 1)) for i in range(keep)}
        for idx, (path, _) in enumerate(indexed):
            if idx not in chosen:
                path.unlink()
        indexed = [row for idx, row in enumerate(indexed) if idx in chosen]
    save_frame_times(
        camera_id,
        [{"frame": path.name, "t_sec": t_sec, "clock": "clip"} for path, t_sec in indexed],
    )
    return len(indexed)
