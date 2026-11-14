"""SVS 5196 (DYAMOND global CO2) — technique: PARAMETER MAPPING (PMSon), as a heartbeat.

The map pulses once per model day (0.8 s of movie = 75 beats per minute, a resting heart).
Each pulse is one heartbeat: "lub" when the red appears, "dub" when it disappears.
Three sound traits carry data; the thump's pitch is fixed so they do not blur each other.
"""
import numpy as np

from jukebox import synth

TITLE = "CO2 heartbeat (parameter mapping)"
DESCRIPTION = ("One heartbeat per daily pulse of the map. 'Lub' (deep thump) at the hour the orange-red area "
               "(dense CO2) grows fastest, 'dub' (shorter, higher thump) at the hour it fades fastest - so the "
               "gap between them is how long the red stays. Louder = a bigger pulse. Left/right = where the red "
               "is on screen. No red, no beat. Data: colours measured from the NASA SVS 5196 movie (GEOS / "
               "DYAMOND model, Jan-Mar 2020) - an index of the picture, not ppm.")

HALF_DAY = 12            # frames (1 frame = 1 model hour)
MIN_PULSE = 0.03         # pulses smaller than this share of the movie's biggest one are not played
LUB = dict(f0=70.0, f1=45.0, length=0.30, fade=0.07)     # Hz at the start / end of the thump, seconds
DUB = dict(f0=95.0, f1=62.0, length=0.20, fade=0.045)
ATTACK_S = 0.012         # swell-in time; shorter = more "click"
OVERTONE = 0.25          # level of the octave above; higher = easier to hear on a laptop, but buzzier
DUB_LEVEL = 0.7


def thump(f0, f1, length, fade, sr):
    """A soft, round drum hit whose pitch falls from f0 to f1. No sharp edges: it swells in over
    ATTACK_S and is faded to exactly zero at its end, so there is no click."""
    t = np.arange(int(length * sr)) / sr
    freq = f1 + (f0 - f1) * np.exp(-t / (fade * 0.6))
    phase = 2 * np.pi * np.cumsum(freq) / sr
    y = np.sin(phase) + OVERTONE * np.sin(2 * phase)       # a little overtone so small speakers still play it
    swell = 0.5 - 0.5 * np.cos(np.pi * np.minimum(1.0, t / ATTACK_S))
    tail = 0.5 + 0.5 * np.cos(np.pi * np.clip((t - 0.6 * length) / (0.4 * length), 0, 1))
    return y * swell * np.exp(-t / fade) * tail


def render(ctx):
    f = ctx.frame_features()
    t = ctx.frame_times
    x = f.table.x.to_numpy()
    plume = f.table.plume.rolling(3, center=True, min_periods=1).mean().to_numpy()    # steadier slopes
    slope = np.gradient(plume)

    beats = []                                             # (lub frame, dub frame, pulse size, pan)
    for i in range(HALF_DAY, len(plume) - HALF_DAY):
        day = plume[i - HALF_DAY:i + HALF_DAY + 1]
        if plume[i] <= 0 or plume[i] < day.max() or plume[i] == plume[i - 1]:
            continue                                       # not the top of a pulse
        lub = i - HALF_DAY + int(np.argmax(slope[i - HALF_DAY:i + 1]))        # red appearing fastest
        dub = i + int(np.argmin(slope[i:i + HALF_DAY + 1]))                   # red fading fastest
        beats.append((lub, dub, plume[i] - day.min(), float(np.clip(4 * (x[i] - 0.5), -1, 1))))
    if not beats:
        return np.zeros((ctx.n_samples, 2))

    biggest = max(b[2] for b in beats)
    out = np.zeros((ctx.n_samples, 2))
    for lub, dub, size, pan in beats:
        if size < MIN_PULSE * biggest:
            continue
        level = 0.25 + 0.75 * np.sqrt(size / biggest)      # louder = bigger pulse
        synth.add_at(out, synth.pan_stereo(thump(sr=ctx.sr, **LUB) * level, pan), float(t[lub]), ctx.sr)
        synth.add_at(out, synth.pan_stereo(thump(sr=ctx.sr, **DUB) * level * DUB_LEVEL, pan), float(t[dub]), ctx.sr)
    return synth.normalize(out)
