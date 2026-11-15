"""Export a still-image SVS page's sonification as a web scene: <name>.wav + a scan-line <name>.mp4.

    uv run python scripts/export_still_scene.py svs5669/aerosols_bands --chapter aerosols

Writes frontend/web/public/data/<chapter>/svs<id>_<script>.wav (the script's full mix, as the explorer plays it)
and .mp4 (the still with a white line crossing it west to east in step with the audio: H.264, yuv420p, no
audio, as frontend/web/README.md asks). The .vtt descriptions are written by hand, and the .peaks.json with
frontend/web/scripts/make_peaks.py. Needs the raw image (python -m jukebox.measure <id>); ffmpeg comes from the
imageio-ffmpeg package.
"""
import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg

from jukebox import pages, preview, sonify, synth

WEB_DATA = Path(__file__).resolve().parents[2] / "frontend" / "web" / "public" / "data"


def scan_video(image: Path, out: Path, duration: float, fps: int = 30) -> None:
    line = f"W*t/{duration:g}"
    graph = (f"[0:v][1:v]overlay=x='{line}-14':y=0:eval=frame:shortest=1[a];"
             f"[a][2:v]overlay=x='{line}-1':y=0:eval=frame:shortest=1,format=yuv420p[v]")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                    "-loop", "1", "-framerate", str(fps), "-i", str(image),
                    "-f", "lavfi", "-i", f"color=c=white@0.14:s=28x2160:r={fps},format=rgba",
                    "-f", "lavfi", "-i", f"color=c=white@0.9:s=3x2160:r={fps},format=rgba",
                    "-filter_complex", graph, "-map", "[v]", "-t", f"{duration:g}",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-tune", "stillimage",
                    "-movflags", "+faststart", "-an", str(out)], check=True)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("script", help='e.g. "svs5669/aerosols_bands" (as for jukebox.preview)')
    p.add_argument("--chapter", required=True, help="folder under frontend/web/public/data/")
    a = p.parse_args(argv)

    path = preview.find_script(a.script)
    viz_id = preview.viz_id_of(path)
    mod = pages.module(viz_id)
    if mod is None or not getattr(mod, "STILL", False):
        p.error(f"SVS {viz_id} is not a measured still image")
    ctx = preview.build_context(viz_id)
    out = WEB_DATA / a.chapter / f"svs{viz_id}_{path.stem}"
    out.parent.mkdir(parents=True, exist_ok=True)

    audio = sonify.run(path, ctx)
    synth.write_wav(out.with_suffix(".wav"), audio, ctx.sr)
    scan_video(pages.raw_path(viz_id), out.with_suffix(".mp4"), ctx.duration)
    print(f"wrote {out}.wav and .mp4 ({ctx.duration:g} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
