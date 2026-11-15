"""Fast sonification loop from the terminal: render a script, play it, and redo it every time you save.

    uv run python -m jukebox.preview co2_15 --start 20 --end 35 --watch
    uv run python -m jukebox.preview co2_15 --set BREATH_GAIN=0.5 --set MASTER_GAIN=0.8

SCRIPT is a path, or a name/prefix of a file in sonifications/ ("co2_15", "svs5196/co2_15_lungs_heart_region").
The whole movie is rendered (about a second for the CO2 scripts) and then the --start/--end window is cut
out, so levels and normalisation are exactly what the explorer plays. The WAV goes to backend/out/preview/.
`--set NAME=VALUE` overrides a constant the script lists in PARAMS (see jukebox.sonify.Param).
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from . import data, measure, paths, sonify, svs, synth

SONIFICATIONS = paths.SONIFICATIONS_DIR
OUT_DIR = paths.OUT_DIR / "preview"
FADE_S = 0.01  # fade at the cut edges so a window never starts or ends with a click


# ---- finding the script and building its context (what the explorer does with Streamlit) ---------------

def find_script(arg: str, root: Path = SONIFICATIONS) -> Path:
    """A path, or the unique script whose name (or "svs<id>/name") equals / starts with `arg`."""
    p = Path(arg)
    if p.is_file():
        return p.resolve()
    key = arg.replace("\\", "/").removesuffix(".py")
    scripts = [q for q in root.rglob("*.py") if not q.name.startswith("_")]
    names = lambda q: (q.stem, f"{q.parent.name}/{q.stem}")  # noqa: E731
    tiers = (lambda q: key in names(q),
             lambda q: any(n.startswith(key + "_") for n in names(q)),
             lambda q: any(n.startswith(key) for n in names(q)))
    for tier in tiers:
        found = [q for q in scripts if tier(q)]
        if len(found) == 1:
            return found[0]
        if found:
            raise ValueError(f"{arg!r} is ambiguous: " + ", ".join(sorted(q.stem for q in found)))
    raise ValueError(f"No sonification script matches {arg!r} under {root}")


def viz_id_of(script: Path) -> int | None:
    m = re.fullmatch(r"svs(\d+)", script.parent.name)
    return int(m.group(1)) if m else None


def build_context(viz_id: int, movie: str | None = None, fps: float | None = None,
                  params: dict | None = None) -> sonify.SonifyContext:
    """Timeline + movie for an SVS page from the committed/downloaded data, with no network when possible.

    A measured page (jukebox.measure) uses its measured movie: `movie` picks one when it has several (SVS 5196).
    """
    if (page := measure.page(viz_id)) is not None:
        movie = page.resolve(movie)
        found = sonify.measured_timeline(viz_id, movie, fps)
        if found is None:
            raise FileNotFoundError(f"SVS {viz_id} movie {movie!r} is not measured yet: "
                                    f"run python -m jukebox.measure {viz_id}")
        timeline = found.timeline
    else:
        years = data.load_frame_years(paths.RAW_DIR / f"svs{viz_id}_time.txt")
        if years is not None:
            timeline = sonify.Timeline([str(y) for y in years], fps or sonify.DEFAULT_FPS)
        else:
            tt = svs.fetch_time_txt(svs.fetch(viz_id))
            if tt is None:
                raise FileNotFoundError(f"SVS {viz_id} has no time.txt: put one in data/raw/svs{viz_id}_time.txt")
            timeline = sonify.Timeline(tt[1], fps or sonify.DEFAULT_FPS)
    return sonify.context_for(viz_id, timeline, movie or "", params=params)


def parse_overrides(items: list[str], available: dict[str, sonify.Param]) -> dict:
    out = {}
    for item in items:
        name, sep, value = item.partition("=")
        if not sep or name not in available:
            raise ValueError(f"--set {item!r}: use NAME=VALUE with NAME one of "
                             f"{', '.join(available) or '(this script declares no PARAMS)'}")
        out[name] = available[name].coerce(value)
    return out


# ---- rendering a window ---------------------------------------------------------------------------------

def cut(y: np.ndarray, sr: int, start: float, end: float) -> np.ndarray:
    """Seconds [start, end) of stereo audio, with short fades at both edges."""
    clip = y[int(round(start * sr)):int(round(end * sr))].copy()
    k = min(int(FADE_S * sr), len(clip) // 2)
    if k:
        ramp = np.linspace(0.0, 1.0, k)[:, None]
        if start > 0:
            clip[:k] *= ramp
        if end * sr < len(y):
            clip[-k:] *= ramp[::-1]
    return clip


def describe_window(ctx: sonify.SonifyContext, start: float, end: float) -> str:
    labels, fps = ctx.timeline.labels, ctx.timeline.fps
    f0, f1 = int(start * fps), min(int(end * fps), len(labels)) - 1
    return f"{start:.1f}-{end:.1f} s = frames {f0}-{f1}: {labels[f0]!r} ... {labels[f1]!r}"


# ---- playing --------------------------------------------------------------------------------------------

class Player:
    """Plays a WAV in the background; a new play() stops the previous one."""

    def __init__(self):
        self.proc: subprocess.Popen | None = None
        self.cmd = next(([c, *a] for c, a in (("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet"]),
                                              ("afplay", []), ("aplay", ["-q"])) if shutil.which(c)), None)

    def stop(self) -> None:
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        elif self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def play(self, path: Path) -> bool:
        self.stop()
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            return True
        if self.cmd:
            self.proc = subprocess.Popen([*self.cmd, str(path)])
            return True
        return False


# ---- command line ---------------------------------------------------------------------------------------

def render_once(args, script: Path, viz_id: int, player: Player | None) -> None:
    t0 = time.perf_counter()
    mod = sonify.load(script)
    specs = sonify.params_of(mod)
    ctx = build_context(viz_id, args.movie, args.fps, parse_overrides(args.set, specs))
    start = args.start
    end = min(args.end if args.end is not None else ctx.duration, ctx.duration)
    if not 0 <= start < end:
        raise ValueError(f"window {start}-{end} s is empty; the movie is {ctx.duration:.1f} s long")
    y = sonify.run(script, ctx)
    took = time.perf_counter() - t0
    clip = cut(y, ctx.sr, start, end)
    if player:
        player.stop()  # Windows keeps the file open while it plays
    out = OUT_DIR / f"{script.stem}.wav"
    synth.write_wav(out, clip, ctx.sr)
    shown = {n: (ctx.params.get(n, p.default)) for n, p in specs.items()}
    print(f"\n{getattr(mod, 'TITLE', script.stem)}  [{describe_window(ctx, start, end)}]")
    print(f"  rendered in {took:.2f} s, peak {np.abs(clip).max():.2f}  ->  {out}")
    if shown:
        print("  params: " + ", ".join(f"{n}={v:g}" for n, v in shown.items()))
    if player and not player.play(out):
        print("  (no audio player found: open the WAV yourself)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m jukebox.preview", description=__doc__.split("\n\n")[0])
    ap.add_argument("script", help="path, or name/prefix of a script in sonifications/ (e.g. co2_15)")
    ap.add_argument("--start", type=float, default=0.0, help="window start, seconds of movie time")
    ap.add_argument("--end", type=float, default=None, help="window end, seconds (default: end of movie)")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="override a PARAMS constant")
    ap.add_argument("--watch", action="store_true", help="re-render and replay whenever a script file is saved")
    ap.add_argument("--no-play", action="store_true", help="only write the WAV")
    ap.add_argument("--viz", type=int, help="SVS page id (default: from the svs<id> folder name)")
    ap.add_argument("--movie", help="SVS 5196 camera move or movie filename (default: orbit)")
    ap.add_argument("--fps", type=float, help="frames per second (default: 30)")
    args = ap.parse_args(argv)
    try:
        script = find_script(args.script)
        viz_id = args.viz or viz_id_of(script)
        if viz_id is None:
            ap.error("this script is not in an svs<id> folder: pass --viz ID")
    except ValueError as e:
        ap.error(str(e))
    player = None if args.no_play else Player()

    def attempt() -> None:
        try:
            render_once(args, script, viz_id, player)
        except Exception:  # keep watching: show the error, fix the file, save again
            traceback.print_exc()

    attempt()
    if not args.watch:
        return 0
    script_files = lambda: [*script.parent.glob("*.py"), *SONIFICATIONS.glob("*.py")]  # noqa: E731
    lib_files = list(Path(__file__).parent.glob("*.py"))
    stamp = lambda files: {f: f.stat().st_mtime_ns for f in files if f.exists()}  # noqa: E731
    seen, lib_seen = stamp(script_files()), stamp(lib_files)
    print(f"\nWatching {script.parent.name}/ - save a script to re-render, Ctrl+C to stop.")
    try:
        while True:
            time.sleep(0.3)
            now = stamp(script_files())
            if now != seen:
                seen = now
                attempt()
            lib_now = stamp(lib_files)
            if lib_now != lib_seen:
                lib_seen = lib_now
                print("  (jukebox/ changed: restart the command to pick that up)")
    except KeyboardInterrupt:
        if player:
            player.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
