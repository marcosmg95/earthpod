"""SVS 5196 (DYAMOND global CO2) — technique: MODEL-BASED sonification.

The picture is turned into a virtual instrument and then played: 8 metal bars, one per vertical
strip of the screen, left to right. The data does not choose the notes (each bar always has the
same pitch); it sets the *physics* of each bar: how much energy it holds and how long it rings.
A mallet runs across the bars once per model day. Offline stand-in for "tap a region to hear it".
"""
import numpy as np

from jukebox import mapping, synth

TITLE = "Struck bars (model-based)"
DESCRIPTION = ("Eight bars = eight screen strips, left (low, left ear) to right (high, right ear). Once per model "
               "day a mallet taps them in order. A strip with no orange-red (dense CO2) answers with a short dull "
               "thud; the more orange it holds, the louder, brighter and longer the bar rings. So you hear where "
               "on screen the CO2 is and how it moves from day to day. Data: colours measured from the NASA "
               "SVS 5196 movie (GEOS / DYAMOND model, Jan-Mar 2020) - an index of the picture, not ppm.")

BARS = 8
FRAMES_PER_SWEEP = 24                                   # one model day
PARTIALS = [(1.0, 1.0), (2.76, 0.6), (5.4, 0.35)]        # a struck bar's overtones (ratio, level)


def strike(freq, energy, sr):
    """One tap on a bar holding `energy` (0..1): more energy = louder, longer, brighter."""
    ring = 0.06 + 1.1 * energy                           # seconds for the sound to fade to ~5 %
    t = np.arange(int(min(ring * 1.5, 2.0) * sr)) / sr
    y = sum(level * energy ** (k * 0.8) * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-3 * t * (1 + k) / ring)
            for k, (ratio, level) in enumerate(PARTIALS) if freq * ratio < sr / 2)
    return y * np.minimum(1.0, t / 0.002) * (0.12 + 0.88 * np.sqrt(energy))


def render(ctx):
    f = ctx.frame_features()
    strips = f.profiles.reshape(len(f.profiles), BARS, -1).mean(axis=2)           # frames x bars
    strips = np.clip(strips / (np.quantile(strips, 0.995) or 1.0), 0, 1)
    freqs = [mapping.midi_to_hz(mapping.degree_to_midi(k, mapping.TONIC_MIDI + 12)) for k in range(BARS)]
    gap = FRAMES_PER_SWEEP / ctx.timeline.fps / BARS                              # seconds between taps

    out = np.zeros((ctx.n_samples, 2))
    for i in range(0, len(strips), FRAMES_PER_SWEEP):
        for k in range(BARS):
            frame = min(i + k * FRAMES_PER_SWEEP // BARS, len(strips) - 1)        # the strip as it is when tapped
            y = strike(freqs[k], float(strips[frame, k]), ctx.sr)
            synth.add_at(out, synth.pan_stereo(y, -0.9 + 1.8 * k / (BARS - 1)), ctx.frame_times[i] + k * gap, ctx.sr)
    return synth.normalize(out)
