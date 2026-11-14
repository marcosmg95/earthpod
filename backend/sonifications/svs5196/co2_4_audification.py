"""SVS 5196 (DYAMOND global CO2) — technique: AUDIFICATION.

The data *is* the sound wave: no notes, no scale. Each frame gives 120 numbers (how much orange-red,
dense CO2, is in each screen column, left to right); 1176 frames = 141 120 samples. That row of
numbers is used as one cycle of the wave and repeated 110 times a second so it lands in hearing range.
"""
import numpy as np

from jukebox import synth

TITLE = "Screen-scan wave (audification)"
DESCRIPTION = ("Each frame's left-to-right profile of orange-red (dense CO2) is played directly as the shape of "
               "the sound wave, 110 cycles per second: silence = no orange on screen, a pure hum = one broad "
               "plume, a buzzy, bright tone = many sharp separate plumes. Left ear = left half of the screen, "
               "right ear = right half. Loudness is not scaled per frame, so the daily pulse is heard as "
               "swelling. Data: colours measured from the NASA SVS 5196 movie (GEOS / DYAMOND model, "
               "Jan-Mar 2020) - an index of the picture, not ppm.")

CYCLES_PER_S = 110.0


def scan(profiles, frame_pos, phase):
    """Wave value at each audio sample: profile row `frame_pos` (blended between frames), column `phase`."""
    n_frames, n_cols = profiles.shape
    i0 = np.clip(np.floor(frame_pos).astype(int), 0, n_frames - 1)
    i1 = np.minimum(i0 + 1, n_frames - 1)
    w = frame_pos - np.floor(frame_pos)
    col = phase * n_cols
    c0 = np.floor(col).astype(int) % n_cols
    c1 = (c0 + 1) % n_cols
    u = col - np.floor(col)
    row = lambda i: profiles[i, c0] * (1 - u) + profiles[i, c1] * u
    return row(i0) * (1 - w) + row(i1) * w


def render(ctx):
    f = ctx.frame_features()
    n = ctx.n_samples
    time = np.arange(n) / ctx.sr
    frame_pos = time * ctx.timeline.fps
    phase = (time * CYCLES_PER_S) % 1.0
    half = f.profiles.shape[1] // 2
    out = np.zeros((n, 2))
    for ch, cols in enumerate((slice(0, half), slice(half, None))):
        p = f.profiles[:, cols]
        p = p - p.mean(axis=1, keepdims=True)          # a speaker cannot play a constant offset
        out[:, ch] = scan(p, frame_pos, phase)
    scale = np.quantile(np.abs(out), 0.999) or 1.0     # one scale for the whole movie
    return np.clip(out / scale, -1, 1) * 0.6
