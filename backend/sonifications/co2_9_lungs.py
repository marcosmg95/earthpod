"""SVS 5196 (DYAMOND global CO2) — breathing with a heartbeat."""
from pathlib import Path

import numpy as np

from jukebox import sonify, synth

TITLE = "Living Earth: lungs and heartbeat"
DESCRIPTION = ("A centered soft breath with a quiet flowing undertone: more tan haze on screen makes it "
               "louder; the breath grows brighter as the haze increases and darker as it decreases. "
               "Over it, the heartbeat follows the growth and fading of the orange-red area, with its "
               "position on screen. Data: colours measured from the NASA SVS 5196 movie (GEOS / DYAMOND "
               "model), not actual breathing, a heartbeat or CO2 in ppm; camera and background affect "
               "these picture indices.")

BREATH_GAIN = 0.07


def render(ctx):
    f = ctx.frame_features()
    n, sr = ctx.n_samples, ctx.sr
    haze = f.resampled("haze", n) / (f.table.haze.max() or 1.0)
    level = np.sqrt(np.clip(haze, 0, 1))
    smooth = f.table.haze.rolling(5, center=True, min_periods=1).mean().to_numpy()
    slope = np.diff(smooth, prepend=smooth[0])
    slope = np.interp(np.linspace(0, len(slope) - 1, n), np.arange(len(slope)), slope)
    rising = 0.5 + 0.5 * np.clip(3 * slope / (np.abs(slope).max() or 1.0), -1, 1)

    inhale = synth.band_noise(n, 300, 900, sr, seed=91)
    exhale = synth.band_noise(n, 180, 500, sr, seed=92)
    flow = synth.band_noise(n, 80, 260, sr, seed=93)
    breath = (0.65 * rising * inhale + (1 - rising) * exhale + 0.18 * flow) * level
    breath = synth.normalize(synth.pan_stereo(breath, 0.0))
    heartbeat = sonify.run(Path(__file__).with_name("co2_7_heartbeat.py"), ctx)
    return synth.normalize(BREATH_GAIN * breath + heartbeat)
