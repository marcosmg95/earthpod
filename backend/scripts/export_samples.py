"""Instrument samples for "How to listen": one short WAV per sound of the aerosols and night-lights scenes.

    uv run python scripts/export_samples.py            # -> frontend/web/public/data/samples/sample_<scene>_NN_<id>.wav

Every sample is made from the real data with the scene's own script, so it sounds exactly like that layer in the
scene (then run frontend/web/scripts/make_peaks.py):
  aerosols     a few seconds of one stem of svs5669/aerosols_bands, cut where the scan crosses that layer's
               clearest example (times below)
  nightlights  one of svs5313/nightlights_three_acts's own sweeps, replayed alone with the measured grids at the
               movie's timing (the script returns one mix, so its layers cannot be cut out)
Each sample fades in/out over FADE_S and peaks at -6 dB, like the CO2 samples.
"""
from pathlib import Path

import numpy as np

from jukebox import nightlights_frames as nf, preview, sonify, synth

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend" / "web" / "public" / "data" / "samples"
SCRIPTS = Path(__file__).resolve().parents[1] / "sonifications"
FADE_S = 0.15
TAIL_S = 1.0                    # ring-out after the last swept note (night lights)

# id, stem, start s, end s (the scan is at longitude -180 + 7.5 * t)
AEROSOLS = [
    ("sulfate_hum", "sulfate", 32.0, 38.0),          # South Asia and Indonesia
    ("dust_grains", "dust", 17.0, 23.0),             # the Saharan plume over the Atlantic
    ("smoke_crackle", "black_carbon", 22.5, 28.5),   # Spain, then southern Africa
    ("sea_salt_surf", "sea_salt", 9.0, 15.0),        # Southern Ocean, then Hurricane Erin
    ("plume_chime", "stops", 15.5, 21.5),            # the two chimes at the start of the dust plume
    ("haze_wind", "haze", 18.0, 24.0),
    ("meridian_ticks", "meridians", 19.5, 25.5),     # 30 W, then the deep tick at Greenwich
]


def finish(y: np.ndarray, sr: int) -> np.ndarray:
    n = len(y)
    t = np.arange(n) / sr
    env = np.clip(np.minimum(t, t[-1] - t) / FADE_S, 0, 1)
    return synth.normalize(y * env[:, None])


def write(scene: str, k: int, name: str, y: np.ndarray, sr: int) -> None:
    path = OUT / f"sample_{scene}_{k:02d}_{name}.wav"
    synth.write_wav(path, finish(y, sr), sr)
    print(f"wrote {path.relative_to(ROOT)} ({len(y) / sr:.1f} s)")


def aerosols() -> None:
    ctx = preview.build_context(5669)
    stems = sonify.render_stems(SCRIPTS / "svs5669" / "aerosols_bands.py", ctx).audio
    for k, (name, stem, t0, t1) in enumerate(AEROSOLS, 1):
        write("aerosols", k, name, stems[stem][int(t0 * ctx.sr):int(t1 * ctx.sr)], ctx.sr)


def nightlights() -> None:
    m = sonify.load(SCRIPTS / "svs5313" / "nightlights_three_acts.py")
    ctx = preview.build_context(5313)
    g, sr, fps = ctx.nightlights_grids(), ctx.sr, nf.FPS

    def sweeps(plays) -> np.ndarray:
        """plays: (t0, width, grid, scale, kwargs) for m._sweep; returns the audio from the first t0."""
        start = min(p[0] for p in plays)
        end = max(p[0] + p[1] for p in plays) + TAIL_S
        out = np.zeros((int((end - start) * sr), 2))
        for t0, width, grid, scale, kw in plays:
            m._sweep(out, grid, t0 - start, width, scale, sr, **kw)
        return out

    # Act 1: one sweep per year, 2012..2023 (plucks), and the brighter-than-2012 bells on top
    world = np.stack([m._pool(y, 32) for y in g["world_light"]])
    growth = np.clip(world - world[0], 0, None)
    years = [(a / fps, 0.85 * (b - a) / fps) for a, b in nf.year_windows("years")]
    plucks = [(t0, w, world[i], m._scale(world), dict(gain=0.16, **m.WORLD)) for i, (t0, w) in enumerate(years)]
    bells = [(t0, w, growth[i], m._scale(growth), dict(gain=0.3, per_col=1, root=m.WORLD["root"],
              steps=m.WORLD["steps"], timbre="bell", octave=12)) for i, (t0, w) in enumerate(years) if i]
    # Act 2: one slow sweep of the change map per colour
    slot = ((nf.SCENES[2][0] - nf.SCENES[1][0] - 18) / fps) / 3
    purple, orange = m._pool(g["world_purple"], 64), m._pool(g["world_orange"], 64)
    # Act 3: each zoom box swept in 2012, then in 2023, with its own instrument and side
    box_light = np.stack([[m._pool(y, 20) for y in b] for b in g["box_light"]])
    tour = (nf.year_windows("zoom_years")[1][0] - nf.BOXES_IN[1]) / fps / len(nf.BOXES)

    samples = [("city_lights_plucks", sweeps(plucks)),
               ("brighter_than_2012_bells", sweeps(bells)),
               ("new_lights_high_bells", sweeps([(0, 0.9 * slot, purple, m._scale(purple), dict(gain=0.3, **m.PURPLE))])),
               ("lights_out_low_plucks", sweeps([(0, 0.9 * slot, orange, m._scale(orange), dict(gain=0.3, **m.ORANGE))]))]
    for k, box in enumerate(nf.BOXES):
        timbre, root = m.BOX_VOICE[box.key]
        kw = dict(pan=box.pan, spread=0.15, gain=0.3, per_col=3, root=root, steps=12, timbre=timbre)
        both = [(i * (tour + 0.4), 0.9 * tour, box_light[k, year], m._scale(box_light), kw)
                for i, year in enumerate((0, len(box_light[k]) - 1))]
        samples.append((f"{box.key}_{timbre}", sweeps(both)))
    for k, (name, y) in enumerate(samples, 1):
        write("nightlights", k, name, y, sr)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    aerosols()
    nightlights()
