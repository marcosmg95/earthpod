"""SVS 5196 (DYAMOND global CO2) — soft bubbles as an auditory icon."""
import numpy as np

from jukebox import synth

TITLE = "Living Earth: bubbling fluid"
DESCRIPTION = ("Soft bubbles become more frequent as the orange-red area covers more of the screen; they "
               "appear left or right with its position. Bubble tails can continue briefly after the orange "
               "disappears. Data: colours measured from the NASA SVS 5196 movie (GEOS / DYAMOND model), "
               "not actual liquid or CO2 in ppm; camera and background affect these picture indices.")

BUBBLES_PER_SECOND_AT_MAX = 12


def render(ctx):
    f = ctx.frame_features()
    n, sr = ctx.n_samples, ctx.sr
    plume = np.clip(f.resampled("plume", n) / (f.table.plume.max() or 1.0), 0, 1)
    pan = np.clip(2 * f.resampled("x", n) - 1, -1, 1)
    rng = np.random.default_rng(519611)
    hits = np.flatnonzero(rng.random(n) < plume * BUBBLES_PER_SECOND_AT_MAX / sr)
    out = np.zeros((n, 2))
    for i in hits:
        bubble = synth.tone(rng.uniform(250, 700), rng.uniform(0.08, 0.18), "soft", sr)
        synth.add_at(out, synth.pan_stereo(bubble * rng.uniform(0.5, 1.0), pan[i]), i / sr, sr)
    return synth.normalize(out)
