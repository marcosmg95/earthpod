"""SVS 5196 (DYAMOND global CO2) — technique: AUDITORY ICONS.

Everyday sounds, no training needed: the planet breathes, fires crackle, wind carries the haze.
"""
import numpy as np

from jukebox import synth

TITLE = "Breath, fire and wind (auditory icons)"
DESCRIPTION = ("The map pulses once a day, so it breathes: a bright in-breath while the orange-red area (dense "
               "CO2) grows, a dark out-breath while it shrinks, louder for bigger pulses. Fire crackles get "
               "denser the more orange there is, and come from the side of the screen where it is. A low wind "
               "follows the tan haze (medium CO2). Data: colours measured from the NASA SVS 5196 movie "
               "(GEOS / DYAMOND model, Jan-Mar 2020) - an index of the picture, not ppm.")

CRACKLES_PER_S_AT_MAX = 45


def render(ctx):
    f = ctx.frame_features()
    n, sr = ctx.n_samples, ctx.sr
    plume = f.resampled("plume", n) / f.table.plume.max()            # 0..1, one value per audio sample
    haze = f.resampled("haze", n)
    haze = (haze - haze.min()) / (np.ptp(haze) or 1.0)
    pan = np.clip(4 * (f.resampled("x", n) - 0.5), -1, 1)

    # breath: rising plume -> in-breath (bright noise), falling -> out-breath (dark noise)
    slope = np.gradient(f.table.plume.rolling(5, center=True, min_periods=1).mean().to_numpy())
    slope = np.interp(np.linspace(0, len(slope) - 1, n), np.arange(len(slope)), slope)
    rising = np.clip(slope / (np.abs(slope).max() or 1.0) * 6, -1, 1) * 0.5 + 0.5      # 0 = falling, 1 = rising
    floor = f.table.plume.rolling(25, center=True, min_periods=1).min().to_numpy()   # that day's quietest hour
    pulse = np.interp(np.linspace(0, len(floor) - 1, n), np.arange(len(floor)), f.table.plume.to_numpy() - floor)
    level = np.sqrt(pulse / (pulse.max() or 1.0))                    # breath = the pulse above the day's floor
    breath = (synth.band_noise(n, 1500, 4500, sr, seed=1) * rising * 0.6
              + synth.band_noise(n, 250, 900, sr, seed=2) * (1 - rising)) * level
    out = synth.pan_stereo(breath, 0.0)

    # wind: low rumble, louder with more haze
    out += synth.pan_stereo(synth.band_noise(n, 60, 220, sr, seed=3) * (0.15 + 0.85 * haze) * 0.5, 0.0)

    # fire: short clicks; how many per second follows the orange area
    rng = np.random.default_rng(5196)
    hits = np.flatnonzero(rng.random(n) < plume * CRACKLES_PER_S_AT_MAX / sr)
    click_n = int(0.012 * sr)
    decay = np.exp(-np.arange(click_n) / (0.002 * sr))
    for i in hits:
        click = rng.standard_normal(click_n) * decay * rng.uniform(0.3, 1.0)
        synth.add_at(out, synth.pan_stereo(click, pan[i]) * 0.2, i / sr, sr)
    return synth.normalize(out)
