"""SVS 5425 (Perpetual Ocean 2: western boundary currents, 2021–2023) — the ocean, its fast currents, a month clock.

A 5-minute movie, so the audio is rendered at 16 kHz (sonify.LONG_SR) and kept to three stems.

Background (has its own meaning, always there):
    ocean    a deep rolling sea: louder the closer the camera is (less black space on screen), brighter while
             the picture is moving fast (strong flow or a camera move)
    months   one soft tick each time the model month changes (a deeper one each January): ~9 s per month
Foreground:
    currents a cello follows the bright white streamlines — the fast surface currents:
             pitch = how much of the screen they cover (ranked over the movie: more = higher),
             pan = where they are on screen; and every beat a harp pluck whose pitch follows their height on
             screen (top = high) and whose loudness follows how fast those streamlines are swirling.

Stem script: every layer has a live level slider (STEMS); the rest of PARAMS needs a re-render.
Iterate: uv run python -m jukebox.preview boundary_currents --start 200 --end 240 --watch
"""
import numpy as np

from jukebox import instruments, mapping, synth
from jukebox.pages import svs5425 as page

TITLE = "Perpetual Ocean 2: boundary currents"
DESCRIPTION = (
    "NASA SVS 5425 flies from a turning globe to the Kuroshio, the Agulhas Current, Brazil and the Gulf Stream "
    "(model time 2021–2023). Background: a deep rolling sea, louder when the camera is close and brighter while "
    "the picture moves fast, and a soft tick for each new model month (deeper each January). Foreground: a cello "
    "follows the bright white streamlines of the fast currents — higher note = more of them on screen, heard where "
    "they are — and a harp plucks every beat, higher when the currents are near the top of the screen and louder "
    "when they swirl faster. Data: brightness and motion measured from the ECCO2 model movie (picture indices, "
    "not current speeds).")

OCEAN_GAIN = 0.30
MONTHS_GAIN = 0.30
CURRENTS_GAIN = 0.60
OUTPUT_GAIN = 1.0

BEAT_S = 0.6
CELLO_BEATS = 4             # the cello changes note at most every 4 beats
HARP_SHARE = 0.6            # harp level relative to the cello inside the currents stem
RANGE_SEMITONES = 14
SMOOTH = 45                 # frames (1.5 s) of smoothing

STEMS = {"ocean": "OCEAN_GAIN", "months": "MONTHS_GAIN", "currents": "CURRENTS_GAIN"}
PARAMS = {"OCEAN_GAIN": (0.0, 1.0), "MONTHS_GAIN": (0.0, 1.0), "CURRENTS_GAIN": (0.0, 1.0),
          "OUTPUT_GAIN": (0.0, 1.5), "BEAT_S": (0.2, 2.0), "CELLO_BEATS": (1, 8), "HARP_SHARE": (0.0, 1.5),
          "RANGE_SEMITONES": (5, 24), "SMOOTH": (1, 150)}


def ocean(f, ctx) -> np.ndarray:
    n, sr = ctx.n_samples, ctx.sr
    near = np.clip(1 - f.column("space", n, sr, SMOOTH) / 0.6, 0, 1)
    motion = f.table.motion.to_numpy(float)
    bright = np.clip(f.per_sample(motion / (np.percentile(motion, 95) or 1), n, sr, SMOOTH), 0, 1)
    low = synth.band_noise(n, 50, 300, sr, seed=5425)
    high = synth.band_noise(n, 300, min(1800, sr / 2.5), sr, seed=5426)
    swell = 0.75 + 0.25 * np.sin(2 * np.pi * np.arange(n) / sr / 7.0)       # slow waves, 7 s
    y = (low + bright * high) * (0.35 + 0.65 * near) * swell
    return synth.normalize(synth.pan_stereo(y, 0.0))


def months(f, ctx) -> np.ndarray:
    out = np.zeros((ctx.n_samples, 2))
    month = [lab[3:] for lab in f.labels]                    # "15 Jan 2021" -> "Jan 2021"
    for k in range(1, f.n_frames):
        if month[k] != month[k - 1]:
            jan = month[k].startswith("Jan")
            y = instruments.tone("marimba", mapping.midi_to_hz(43 if jan else 79), 0.3, ctx.sr) * (1 if jan else 0.5)
            synth.add_at(out, synth.pan_stereo(y, 0.0), k / f.fps, ctx.sr)
    return synth.normalize(out)


def currents(f, ctx) -> np.ndarray:
    t_ = f.table
    smooth = lambda c: t_[c].rolling(SMOOTH, center=True, min_periods=1).mean().to_numpy(float)  # noqa: E731
    cover, x, y, swirl = smooth("current"), smooth("cur_x"), smooth("cur_y"), smooth("swirl")
    rank = instruments.ranks(cover)
    swirl = np.clip(swirl / (np.percentile(swirl, 95) or 1), 0, 1)
    cello_notes = instruments.scale_notes(45, RANGE_SEMITONES)
    harp_notes = instruments.scale_notes(62, 19)
    out = np.zeros((ctx.n_samples, 2))
    beat, b = BEAT_S, 0
    while b * beat < ctx.duration:
        t = b * beat
        k = min(int(t * f.fps), f.n_frames - 1)
        pan = float(np.clip(2 * x[k] - 1, -1, 1)) * 0.8
        if b % CELLO_BEATS == 0:
            m = cello_notes[int(round(rank[k] * (len(cello_notes) - 1)))]
            yv = instruments.tone("cello", mapping.midi_to_hz(m), beat * CELLO_BEATS * 1.05, ctx.sr)
            synth.add_at(out, synth.pan_stereo(yv * (0.5 + 0.5 * rank[k]), pan), t, ctx.sr)
        h = harp_notes[int(round((1 - np.clip(y[k], 0, 1)) * (len(harp_notes) - 1)))]
        yh = instruments.tone("harp", mapping.midi_to_hz(h), beat, ctx.sr) * HARP_SHARE * (0.1 + 0.9 * swirl[k])
        synth.add_at(out, synth.pan_stereo(yh, pan), t, ctx.sr)
        b += 1
    return synth.normalize(out)


def render(ctx):
    f = ctx.page_features()
    return {"ocean": ocean(f, ctx), "months": months(f, ctx), "currents": currents(f, ctx)}
