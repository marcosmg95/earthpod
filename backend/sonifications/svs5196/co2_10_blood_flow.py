"""SVS 5196 (DYAMOND global CO2) — a continuous flowing-body metaphor."""
import numpy as np

from jukebox import synth

TITLE = "Living Earth: flowing blood"
DESCRIPTION = ("A continuous soft internal rush, without a heartbeat: more orange-red area makes it louder, "
               "and it moves left or right with the orange on screen. Data: colours measured from the NASA "
               "SVS 5196 movie (GEOS / DYAMOND model), not actual blood flow or CO2 in ppm; camera and "
               "background affect these picture indices.")


def render(ctx):
    f = ctx.frame_features()
    n, sr = ctx.n_samples, ctx.sr
    plume = f.resampled("plume", n) / (f.table.plume.max() or 1.0)
    level = np.sqrt(np.clip(plume, 0, 1))
    pan = np.clip(2 * f.resampled("x", n) - 1, -1, 1)
    deep = synth.band_noise(n, 90, 450, sr, seed=101)
    rush = synth.band_noise(n, 400, 1400, sr, seed=102)
    return synth.normalize(synth.pan_stereo((deep + 0.3 * rush) * level, pan))
