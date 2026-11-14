"""Re-encode movies to H.264 MP4, the codec every browser and video editor plays.

Some SVS movies are H.265 (e.g. SVS 5313's EIC movie) or wider than H.264 decoders accept (7680 px).
Uses the ffmpeg binary bundled with the `imageio-ffmpeg` package, so no system ffmpeg is needed.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

MAX_WIDTH = 4096  # H.264 level 5.1/5.2 limit; wider movies are scaled down, keeping the aspect ratio


def ffmpeg_exe() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def probe(path: Path) -> tuple[str, str, int] | None:
    """(codec, pixel format, width) of the first video stream, read from ffmpeg's stream info."""
    info = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Video: (\w+)[^,]*, (\w+)[^,]*,.*?(\d{2,5})x(\d{2,5})", info)
    return (m.group(1), m.group(2), int(m.group(3))) if m else None


def is_browser_h264(path: Path) -> bool:
    p = probe(path)
    return p is not None and p[0] == "h264" and p[1] == "yuv420p" and p[2] <= MAX_WIDTH


def h264_args(src: Path, dst: Path, crf: int = 20) -> list[str]:
    return [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
            "-map", "0:v:0", "-an",
            "-vf", f"scale='min({MAX_WIDTH},iw)':-2",
            "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart",
            str(dst)]


def to_h264(movie: bytes, crf: int = 20) -> bytes:
    """Return `movie` as a video-only H.264 MP4 (yuv420p, faststart, width <= MAX_WIDTH).

    Already-compatible H.264 movies are returned unchanged. Raises RuntimeError if ffmpeg fails.
    """
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "in", Path(tmp) / "out.mp4"
        src.write_bytes(movie)
        if is_browser_h264(src):
            return movie
        r = subprocess.run(h264_args(src, dst, crf), capture_output=True, text=True)
        if r.returncode != 0 or not dst.exists():
            raise RuntimeError(f"ffmpeg could not re-encode the movie: {r.stderr.strip()[-500:]}")
        return dst.read_bytes()


def h264_filename(filename: str) -> str:
    """`x_h265.mp4` -> `x_h264.mp4`; otherwise `x.mov` -> `x_h264.mp4`."""
    stem = Path(filename).stem
    stem = re.sub(r"(?i)[_-]?(h265|hevc|h264)$", "", stem)
    return f"{stem}_h264.mp4"
