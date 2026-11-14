"""NASA SVS 5313 night lights as a quiet electrical nervous system."""
import numpy as np

from jukebox import nightlights_frames, synth

TITLE = "Night lights: nervous system"
DESCRIPTION = ("A quiet electrical murmur follows bright areas in NASA SVS 5313's EIC movie: "
               "more or brighter pixels make it louder, their screen position controls left/right, "
               "and faster visual changes make it shimmer faster. These are picture indices, "
               "not radiance or nerve activity; map details, overlays and zooms affect the sound.")


def render(ctx):
    f = ctx.nightlights_features()
    n, sr = ctx.n_samples, ctx.sr
    light = f.resampled("light", n, sr)
    level = np.sqrt(np.clip(light / (f.table.light.max() or 1.0), 0, 1))
    pan = np.clip(2 * f.resampled("x", n, sr) - 1, -1, 1)
    smooth = f.table.light.rolling(5, center=True, min_periods=1).mean().to_numpy()
    change = np.abs(np.diff(smooth, prepend=smooth[0]))
    change = np.interp(np.arange(n) * nightlights_frames.FPS / sr, np.arange(len(change)), change)
    rate = 3 + 15 * change / (change.max() or 1.0)
    shimmer = 0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(rate) / sr)
    murmur = synth.band_noise(n, 500, 2200, sr, seed=121) * (0.3 + 0.7 * shimmer) * level
    return synth.normalize(synth.pan_stereo(murmur, pan))
