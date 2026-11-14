"""SVS 4960 (a 3D atmospheric river, Oct–Dec 2010) — the river of vapour, the rain it drops, and model time.

A 5-minute movie, so the audio is rendered at 16 kHz (sonify.LONG_SR) and kept to three stems.

Background (has its own meaning, always there):
    clock    a soft tick every CLOCK_HOURS of model time; model time in this movie jumps and replays, so the
             ticks speed up, slow down or stop with it — and a short falling swoop marks each jump back in time
Foreground:
    river    rushing air for the band of moisture (the translucent blue): louder the more of the screen it
             covers, heard where it is on screen; above it a flute holds a note that rises with the amount of
             moisture (ranked over the movie), changing every NOTE_S seconds
    rain     drops: short high plucks, more of them the more rain colours (yellow -> red) are on screen,
             scattered across the stereo field

Stem script: every layer has a live level slider (STEMS); the rest of PARAMS needs a re-render.
Iterate: uv run python -m jukebox.preview river_rain_clock --start 160 --end 200 --watch
"""
import numpy as np

from jukebox import instruments, mapping, synth
from jukebox.pages import svs4960 as page

TITLE = "Atmospheric river: vapour, rain and model time"
DESCRIPTION = (
    "NASA SVS 4960 follows an atmospheric river across the Pacific to California and over the Sierra Nevada "
    "(model time, October–December 2010). Background: a soft tick every few hours of model time — the movie's "
    "clock jumps and replays, so the ticks speed up, slow down or stop with it, and a short falling swoop marks "
    "each jump back in time. Foreground: rushing air for the river of moisture (louder the more of the screen it "
    "covers, heard where it is) with a flute above it that rises with the amount of moisture, and rain drops — "
    "more drops the more rain colours are on screen. Data: colours measured from the model movie (picture "
    "indices, not water vapour transport or rain rates); dates read from the page's dates-only movie.")

CLOCK_GAIN = 0.30
RIVER_GAIN = 0.55
RAIN_GAIN = 0.40
OUTPUT_GAIN = 1.0

CLOCK_HOURS = 6.0
NOTE_S = 1.2
FLUTE_SHARE = 0.5           # flute level relative to the rushing air inside the river stem
DROPS_PER_S = 14.0          # drop rate when the rain share is at its busiest
RANGE_SEMITONES = 14
SMOOTH = 30

STEMS = {"clock": "CLOCK_GAIN", "river": "RIVER_GAIN", "rain": "RAIN_GAIN"}
PARAMS = {"CLOCK_GAIN": (0.0, 1.0), "RIVER_GAIN": (0.0, 1.0), "RAIN_GAIN": (0.0, 1.0), "OUTPUT_GAIN": (0.0, 1.5),
          "CLOCK_HOURS": (1.0, 24.0), "NOTE_S": (0.4, 4.0), "FLUTE_SHARE": (0.0, 1.5),
          "DROPS_PER_S": (1.0, 40.0), "RANGE_SEMITONES": (5, 24), "SMOOTH": (1, 120)}


def rel(v: np.ndarray, pct: float = 98) -> np.ndarray:
    return np.clip(v / (np.percentile(v, pct) or 1.0), 0, 1)


def clock(f, ctx) -> np.ndarray:
    out = np.zeros((ctx.n_samples, 2))
    hours = f.table.day.to_numpy(float) * 24
    step = hours // CLOCK_HOURS
    tick = instruments.tone("marimba", mapping.midi_to_hz(79), 0.25, ctx.sr) * 0.5
    t = np.arange(int(0.35 * ctx.sr)) / ctx.sr
    swoop = np.sin(2 * np.pi * np.cumsum(np.linspace(900, 250, len(t))) / ctx.sr) * np.exp(-6 * t) * 0.6
    last_swoop = -10.0
    for k in range(1, f.n_frames):
        if step[k] > step[k - 1]:
            synth.add_at(out, synth.pan_stereo(tick, 0.0), k / f.fps, ctx.sr)
        elif hours[k] < hours[k - 1] - CLOCK_HOURS and k / f.fps - last_swoop > 0.5:
            synth.add_at(out, synth.pan_stereo(swoop, 0.0), k / f.fps, ctx.sr)
            last_swoop = k / f.fps
    return synth.normalize(out)


def river(f, ctx) -> np.ndarray:
    n, sr = ctx.n_samples, ctx.sr
    moisture = f.table.moisture.to_numpy(float)
    level = np.sqrt(f.per_sample(rel(moisture), n, sr, SMOOTH))
    pan = np.clip(2 * f.column("moist_x", n, sr, SMOOTH) - 1, -1, 1) * 0.8
    rush = synth.band_noise(n, 250, min(3000, sr / 2.5), sr, seed=4960)
    out = synth.pan_stereo(rush * level, pan)
    smooth = f.table.moisture.rolling(SMOOTH, center=True, min_periods=1).mean().to_numpy(float)
    rank, amount = instruments.ranks(smooth), rel(smooth)
    notes = instruments.scale_notes(62, RANGE_SEMITONES)
    flute = np.zeros((n, 2))
    t = 0.0
    while t < ctx.duration:
        k = min(int(t * f.fps), f.n_frames - 1)
        if amount[k] > 0.05:
            y = instruments.tone("flute", mapping.midi_to_hz(notes[int(round(rank[k] * (len(notes) - 1)))]),
                                 NOTE_S * 1.05, sr)
            p = float(pan[min(int(t * sr), n - 1)])
            synth.add_at(flute, synth.pan_stereo(y * (0.3 + 0.7 * amount[k]), p), t, sr)
        t += NOTE_S
    return synth.normalize(synth.normalize(out) + FLUTE_SHARE * synth.normalize(flute))


def rain(f, ctx) -> np.ndarray:
    out = np.zeros((ctx.n_samples, 2))
    amount = rel(f.table.rain.rolling(SMOOTH, center=True, min_periods=1).mean().to_numpy(float), 99)
    rng = np.random.default_rng(4961)
    notes = instruments.scale_notes(81, 12)
    dt = 1.0 / 60
    t = 0.0
    while t < ctx.duration:
        k = min(int(t * f.fps), f.n_frames - 1)
        if rng.random() < DROPS_PER_S * amount[k] * dt:
            y = synth.tone(mapping.midi_to_hz(notes[rng.integers(len(notes))]), 0.15, "pluck", ctx.sr)
            synth.add_at(out, synth.pan_stereo(y * (0.5 + 0.5 * rng.random()), rng.uniform(-0.9, 0.9)), t, ctx.sr)
        t += dt
    return synth.normalize(out)


def render(ctx):
    f = ctx.page_features()
    return {"clock": clock(f, ctx), "river": river(f, ctx), "rain": rain(f, ctx)}
