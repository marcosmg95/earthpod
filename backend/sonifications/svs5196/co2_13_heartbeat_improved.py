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
               "gap between them is how long the red stays. Strength is a scale: the less CO2 colour on screen "
               "(red + tan, averaged over a day), the stronger the beat; the more CO2, the fainter. Left/right = where the red "
               "is on screen. No red, no beat. Data: colours measured from the NASA SVS 5196 movie (GEOS / "
               "DYAMOND model, Jan-Mar 2020) - an index of the picture, not ppm.")

HALF_DAY = 12
MIN_PULSE = 0.03
LUB = dict(f0=68.0, f1=52.0, length=0.18, attack=0.030)
DUB = dict(f0=82.0, f1=64.0, length=0.14, attack=0.022)
DUB_LEVEL = 0.70
MASTER_GAIN = 0.65
WEAKEST = 0.08          # loudness of a beat at the most-CO2 moment (1.0 = at the least-CO2 moment)
# A strong beat is not only louder but fuller: a soft overtone (2x the thump's pitch, audible on
# small speakers that cannot play the ~60 Hz body) is mixed in by strength. It uses the thump's own
# slow, smooth envelope, so it adds warmth without a click.
WARM_PITCH = 2.0
WARM_LEVEL = 0.6
PAN_WIDTH = 4.0         # left/right spread: pan = PAN_WIDTH * (x - 0.5), clipped to -1..1 (0 = centred)

# Tunable without editing: sliders in the explorer, --set NAME=VALUE in `python -m jukebox.preview`.
PARAMS = {"MASTER_GAIN": (0.0, 1.0), "DUB_LEVEL": (0.0, 1.5), "WEAKEST": (0.0, 1.0), "WARM_LEVEL": (0.0, 1.5),
          "PAN_WIDTH": (0.0, 6.0)}


def thump(f0, f1, length, attack, sr):
    n = int(length * sr)
    t = np.arange(n) / sr
    freq = f1 + (f0 - f1) * 0.5 * (1.0 + np.cos(np.pi * t / length))
    phase = 2 * np.pi * np.cumsum(freq) / sr
    y = np.sin(phase)

    env = np.ones(n)
    att = int(attack * sr)
    rel = n - att
    env[:att] = 0.5 - 0.5 * np.cos(np.pi * np.arange(att) / att)
    env[att:] = 0.5 + 0.5 * np.cos(np.pi * np.arange(rel) / rel)
    return y * (env ** 2)


def render(ctx):
    f = ctx.frame_features()
    t = ctx.frame_times
    x = f.table.x.to_numpy()
    plume = f.table.plume.rolling(3, center=True, min_periods=1).mean().to_numpy()
    slope = np.gradient(plume)

    beats = []
    last_peak = -HALF_DAY * 2
    for i in range(HALF_DAY, len(plume) - HALF_DAY):
        if i - last_peak < HALF_DAY:
            continue
        day = plume[i - HALF_DAY:i + HALF_DAY + 1]
        if plume[i] <= 0 or plume[i] < day.max():
            continue
        last_peak = i
        lub = i - HALF_DAY + int(np.argmax(slope[i - HALF_DAY:i + 1]))
        dub = max(lub + 6, i + int(np.argmin(slope[i:i + HALF_DAY + 1])))
        if dub >= len(t) - 6:
            continue
        beats.append((lub, dub, plume[i] - day.min(), float(np.clip(PAN_WIDTH * (x[i] - 0.5), -1, 1))))
    if not beats:
        return np.zeros((ctx.n_samples, 2))

    # Strength scale: total CO2 on screen (red + tan), averaged over one day so the daily pulse
    # does not shake it. Least CO2 in the movie -> strongest beat, most CO2 -> weakest beat.
    co2 = (f.table.plume + f.table.haze).rolling(2 * HALF_DAY, center=True, min_periods=1).mean().to_numpy()
    # The scale spans the movie's own range, but never less than 20% of its peak, so tiny
    # wiggles in a near-constant movie are not blown up into a full loud-to-faint swing.
    span = max(co2.max() - co2.min(), 0.2 * co2.max(), 1e-9)
    strength = 1.0 - (co2 - co2.min()) / span

    biggest = max(b[2] for b in beats)
    out = np.zeros((ctx.n_samples, 2))
    def warm(shape):
        return thump(WARM_PITCH * shape["f0"], WARM_PITCH * shape["f1"], shape["length"], shape["attack"], ctx.sr)

    lub_body, lub_warm = thump(sr=ctx.sr, **LUB), warm(LUB)
    dub_body, dub_warm = thump(sr=ctx.sr, **DUB) * DUB_LEVEL, warm(DUB) * DUB_LEVEL

    for lub, dub, size, pan in beats:
        if size < MIN_PULSE * biggest:
            continue
        s = strength[lub]
        level = WEAKEST + (1.0 - WEAKEST) * s ** 1.5
        full = WARM_LEVEL * s ** 2            # weak beats: a muffled thud; strong beats: a fuller thud
        synth.add_at(out, synth.pan_stereo((lub_body + full * lub_warm) * level, pan), float(t[lub]), ctx.sr)
        synth.add_at(out, synth.pan_stereo((dub_body + full * dub_warm) * level, pan), float(t[dub]), ctx.sr)
    return synth.normalize(out) * MASTER_GAIN