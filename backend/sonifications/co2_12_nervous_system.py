"""SVS 5196 (DYAMOND global CO2) — a quiet electrical-body metaphor."""
import numpy as np

from jukebox import synth

TITLE = "Living Earth: nervous system"
DESCRIPTION = ("A quiet electrical murmur follows the orange-red area and its screen position. Faster changes "
               "in that area make the murmur shimmer more quickly. Data: colours measured from the NASA "
               "SVS 5196 movie (GEOS / DYAMOND model), not actual nerve activity or CO2 in ppm; camera "
               "and background affect these picture indices.")


def render(ctx):
    f = ctx.frame_features()
    n, sr = ctx.n_samples, ctx.sr
    plume = f.resampled("plume", n) / (f.table.plume.max() or 1.0)
    level = np.sqrt(np.clip(plume, 0, 1))
    pan = np.clip(2 * f.resampled("x", n) - 1, -1, 1)
    smooth = f.table.plume.rolling(5, center=True, min_periods=1).mean().to_numpy()
    change = np.abs(np.diff(smooth, prepend=smooth[0]))
    change = np.interp(np.linspace(0, len(change) - 1, n), np.arange(len(change)), change)
    rate = 3 + 15 * change / (change.max() or 1.0)
    shimmer = 0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(rate) / sr)
    murmur = synth.band_noise(n, 500, 2200, sr, seed=121) * (0.3 + 0.7 * shimmer) * level
    return synth.normalize(synth.pan_stereo(murmur, pan))
