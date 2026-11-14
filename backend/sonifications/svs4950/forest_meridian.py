"""SVS 4950 (GEDI forest height) — the meridian facing you sings its forests as the globe turns.

Background (has its own meaning, always there):
    ocean   a low hush, louder the more of the visible globe is sea
    leaves  a high rustle, louder the more land is in view and brighter the taller its forests look
    meridians  a soft tick each time a 30° meridian faces the camera (a deeper one at 0°, Greenwich)
Foreground:
    meridian  every beat, a harp arpeggio runs down the line of longitude at the centre of the globe, north to
              south: one note per band of latitude that has land (higher note = further north), louder where the
              forest there is taller. Deserts and grassland are quiet, rainforest rings.
    tall      a cello holds the latitude of the tallest-looking forest on that line while it crosses (the top
              TALL_PCT of this movie's land), louder the taller; it moves with the tall forest's side on screen.
Levels are relative to this movie: lighting brightens some regions (e.g. the far north), so these are
picture indices of the colour bar, not metres.

Stem script: every layer has a live level slider (STEMS); the rest of PARAMS needs a re-render.
Iterate: uv run python -m jukebox.preview forest_meridian --start 15 --end 30 --watch
"""
import numpy as np

from jukebox import instruments, mapping, synth
from jukebox.pages import svs4950 as page

TITLE = "Forest height: the meridian sings"
DESCRIPTION = (
    "As the globe in NASA SVS 4950 turns, the line of longitude facing you is read from north to south. "
    "Background: a low ocean hush (more sea in view = louder), a high leaf rustle (more land = louder, taller "
    "forest = brighter) and a soft tick each time a 30-degree meridian faces you (deeper at Greenwich). "
    "Foreground: every beat a harp arpeggio runs down that meridian, one note per band of latitude with land "
    "(higher note = further north), louder where the forest is taller — deserts are quiet, rainforests ring. "
    "A cello holds the latitude of the tallest-looking forest on the line while it crosses. Loudness is relative "
    "to this movie (its greenest, brightest land plays loudest). Data: colours measured from the GEDI forest-height "
    "movie (bright green = tall per its colour bar); picture indices, not metres — the virtual sun and the "
    "exaggerated height also brighten some regions, such as the far north.")

OCEAN_GAIN = 0.20
LEAVES_GAIN = 0.18
TICK_GAIN = 0.30
MERIDIAN_GAIN = 0.60
TALL_GAIN = 0.40
OUTPUT_GAIN = 1.0

BEAT_S = 0.5                # one arpeggio per beat
ARP_SPAN = 0.6              # share of the beat the arpeggio takes, north -> south
MIN_LAND = 0.25             # a latitude band sings only if this share of it is land
QUIET = 0.03                # canopy index at which a note is barely audible
LOUD_PCT = 97               # canopy index at this percentile of the movie's land plays at full level
TALL_PCT = 85               # the cello comes in above this percentile of the movie's land canopy
LOW_NOTE = 50               # D3: the southernmost band; each band one step up the pentatonic
SMOOTH = 15                 # frames of smoothing for the background levels

STEMS = {"ocean": "OCEAN_GAIN", "leaves": "LEAVES_GAIN", "meridians": "TICK_GAIN",
         "meridian": "MERIDIAN_GAIN", "tall": "TALL_GAIN"}
PARAMS = {"OCEAN_GAIN": (0.0, 1.0), "LEAVES_GAIN": (0.0, 1.0), "TICK_GAIN": (0.0, 1.0),
          "MERIDIAN_GAIN": (0.0, 1.0), "TALL_GAIN": (0.0, 1.0), "OUTPUT_GAIN": (0.0, 1.5),
          "BEAT_S": (0.2, 1.5), "ARP_SPAN": (0.2, 1.0), "MIN_LAND": (0.05, 0.8), "QUIET": (0.0, 0.3),
          "LOUD_PCT": (50, 100), "TALL_PCT": (50, 99), "SMOOTH": (1, 60)}


def band_notes() -> list[int]:
    """One pentatonic note per latitude band, north (index 0) highest."""
    notes = instruments.scale_notes(LOW_NOTE, 40)[:page.ROWS]
    return notes[::-1]


def land_canopy(f) -> np.ndarray:
    """Canopy index of every (frame, band) that has enough land: the scale the levels are relative to."""
    return f.arrays["meridian"][f.arrays["land_rows"] >= MIN_LAND]


def meridian(f, ctx) -> np.ndarray:
    canopy, land = f.arrays["meridian"], f.arrays["land_rows"]
    loud = max(float(np.percentile(land_canopy(f), LOUD_PCT)), QUIET + 1e-3)
    notes = band_notes()
    out = np.zeros((ctx.n_samples, 2))
    t = 0.0
    while t < ctx.duration:
        k = min(int(t * f.fps), f.n_frames - 1)
        rows = [r for r in range(page.ROWS) if land[k, r] >= MIN_LAND]
        for j, r in enumerate(rows):
            level = np.clip((canopy[k, r] - QUIET) / (loud - QUIET), 0, 1)
            if level <= 0:
                continue
            start = t + ARP_SPAN * BEAT_S * j / max(len(rows), 1)
            y = instruments.tone("harp", mapping.midi_to_hz(notes[r]), BEAT_S, ctx.sr) * (0.15 + 0.85 * level)
            synth.add_at(out, synth.pan_stereo(y, 0.0), start, ctx.sr)
        t += BEAT_S
    return synth.normalize(out)


def tall(f, ctx) -> np.ndarray:
    canopy, land = f.arrays["meridian"], f.arrays["land_rows"]
    notes = [n - 12 for n in band_notes()]
    pan = np.clip(f.table.tall_x.to_numpy(float), -1, 1)
    values = land_canopy(f)
    tall_from, top = np.percentile(values, TALL_PCT), np.percentile(values, 99.5)
    out = np.zeros((ctx.n_samples, 2))
    t = 0.0
    while t < ctx.duration:
        k = min(int(t * f.fps), f.n_frames - 1)
        score = canopy[k] * (land[k] >= MIN_LAND)
        r = int(score.argmax())
        if score[r] >= tall_from:
            level = min(1.0, (score[r] - tall_from) / max(top - tall_from, 1e-6))
            y = instruments.tone("cello", mapping.midi_to_hz(notes[r]), BEAT_S * 2 * 1.05, ctx.sr)
            synth.add_at(out, synth.pan_stereo(y * (0.4 + 0.6 * level), float(pan[k]) * 0.6), t, ctx.sr)
        t += BEAT_S * 2
    return synth.normalize(out)


def backgrounds(f, ctx) -> tuple[np.ndarray, np.ndarray]:
    n, sr = ctx.n_samples, ctx.sr
    land = f.column("land", n, sr, SMOOTH)
    canopy = f.column("canopy", n, sr, SMOOTH)
    sea = synth.band_noise(n, 60, 400, sr, seed=4950)
    hi = min(7000, sr / 2.2)
    dark, bright = synth.band_noise(n, 1500, hi * 0.6, sr, seed=4951), synth.band_noise(n, 3000, hi, sr, seed=4952)
    gust = 0.6 + 0.4 * f.per_sample(np.random.default_rng(1).random(f.n_frames), n, sr, smooth=45)
    c = np.clip((canopy - 0.15) / 0.2, 0, 1)
    leaves = ((1 - c) * dark + c * bright) * np.sqrt(np.clip(land / 0.45, 0, 1)) * gust
    ocean = sea * np.sqrt(np.clip(1 - land, 0, 1))
    return synth.normalize(synth.pan_stereo(ocean, 0.0)), synth.normalize(synth.pan_stereo(leaves, 0.0))


def meridian_ticks(f, ctx) -> np.ndarray:
    out = np.zeros((ctx.n_samples, 2))
    lon = f.table.lon.to_numpy(float)
    for k in range(1, f.n_frames):
        a, b = lon[k - 1], lon[k]
        if abs(a - b) > 180:          # wrapped past 180°
            continue
        for m in range(-150, 181, 30):
            if min(a, b) < m <= max(a, b):
                deep = m == 0
                y = instruments.tone("marimba", mapping.midi_to_hz(38 if deep else 74), 0.3, ctx.sr)
                synth.add_at(out, synth.pan_stereo(y * (1.0 if deep else 0.5), 0.0), k / f.fps, ctx.sr)
    return synth.normalize(out)


def render(ctx):
    f = ctx.page_features()
    ocean, leaves = backgrounds(f, ctx)
    return {"ocean": ocean, "leaves": leaves, "meridians": meridian_ticks(f, ctx),
            "meridian": meridian(f, ctx), "tall": tall(f, ctx)}
