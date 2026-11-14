"""SVS 5011 (lightning seen from the ISS) — crackles where storms flash, thunder, and the seasons swinging.

Background (has its own meaning, always there):
    seasons  a soft chord that rises when most lightning is north of the equator and sinks when it is south;
             louder the more lightning is on the map (the hemispheres swap every ~12 s of movie)
    thunder  a low rumble, as loud as the new flashes appearing on the map right now
Foreground:
    crackle  each new storm cell (10° x 10°) that lights up plays a short electric click, panned to its longitude,
             pitched by its latitude (north high); at most CRACKLES_PER_FRAME per frame, the brightest first
    americas / africa_europe / asia_oceania   three struck instruments, panned west -> east, one note per beat;
             pitch = how much lightning that region has now compared with its own range (higher = busier),
             marimba (Americas), harp (Africa and Europe), vibraphone (Asia and Oceania)

Stem script: every layer has a live level slider (STEMS); the rest of PARAMS needs a re-render.
Iterate: uv run python -m jukebox.preview storm_map --start 10 --end 25 --watch
"""
import numpy as np

from jukebox import instruments, mapping, synth
from jukebox.pages import svs5011 as page

TITLE = "Lightning: storm map with thunder and seasons"
DESCRIPTION = (
    "Lightning detected from the International Space Station (NASA SVS 5011), map view. Background: a soft chord "
    "that rises while most lightning is in the northern hemisphere and sinks while it is in the southern one "
    "(louder with more lightning on the map), and a low thunder rumble as loud as the new flashes appearing. "
    "Foreground: a short electric click for each patch of the map that lights up, heard at its longitude (west "
    "left, east right) and pitched by its latitude (north high); and three instruments for the Americas "
    "(marimba, left), Africa and Europe (harp, centre) and Asia and Oceania (vibraphone, right): higher note = "
    "busier than usual for that region. Data: yellow dots measured on the movie's map (picture indices, not "
    "flash counts); the movie prints no dates, so the timeline names the season it shows.")

SEASONS_GAIN = 0.25
THUNDER_GAIN = 0.30
CRACKLE_GAIN = 0.35
AMERICAS_GAIN = 0.40
AFRICA_EUROPE_GAIN = 0.40
ASIA_OCEANIA_GAIN = 0.40
OUTPUT_GAIN = 1.0

CRACKLES_PER_FRAME = 2
CRACKLE_RISE = 0.25         # a cell "lights up" when its value jumps by this much in a frame
BEAT_S = 0.25
RANGE_SEMITONES = 14
SMOOTH = 31                 # frames of smoothing for seasons / region levels

STEMS = {"seasons": "SEASONS_GAIN", "thunder": "THUNDER_GAIN", "crackle": "CRACKLE_GAIN",
         "americas": "AMERICAS_GAIN", "africa_europe": "AFRICA_EUROPE_GAIN", "asia_oceania": "ASIA_OCEANIA_GAIN"}
PARAMS = {"SEASONS_GAIN": (0.0, 1.0), "THUNDER_GAIN": (0.0, 1.0), "CRACKLE_GAIN": (0.0, 1.0),
          "AMERICAS_GAIN": (0.0, 1.0), "AFRICA_EUROPE_GAIN": (0.0, 1.0), "ASIA_OCEANIA_GAIN": (0.0, 1.0),
          "OUTPUT_GAIN": (0.0, 1.5), "CRACKLES_PER_FRAME": (0, 6), "CRACKLE_RISE": (0.05, 0.8),
          "BEAT_S": (0.1, 1.0), "RANGE_SEMITONES": (5, 24), "SMOOTH": (1, 120)}

REGIONS = {"americas": ("marimba", 55, -0.75), "africa_europe": ("harp", 57, 0.0),
           "asia_oceania": ("vibraphone", 62, 0.75)}
NORTH_CHORD = (74, 77, 81)   # D5 F5 A5
SOUTH_CHORD = (50, 53, 57)   # D3 F3 A3


def seasons(f, ctx) -> np.ndarray:
    n, sr = ctx.n_samples, ctx.sr
    north = f.column("north", n, sr, SMOOTH)
    amount = f.table.flashes.to_numpy(float)
    level = np.sqrt(np.clip(f.per_sample(amount / (np.percentile(amount, 98) or 1), n, sr, SMOOTH), 0, 1))
    t = np.arange(n) / sr
    def chord(notes):
        return sum(np.sin(2 * np.pi * mapping.midi_to_hz(m) * t) for m in notes) / len(notes)
    y = (north * chord(NORTH_CHORD) + (1 - north) * chord(SOUTH_CHORD)) * level
    return synth.normalize(synth.pan_stereo(y, 0.0))


def thunder(f, ctx) -> np.ndarray:
    n, sr = ctx.n_samples, ctx.sr
    new = f.table.new.to_numpy(float)
    level = np.clip(f.per_sample(new / (np.percentile(new, 99) or 1), n, sr, smooth=9), 0, 1.2)
    rumble = synth.band_noise(n, 30, 160, sr, seed=5011)
    return synth.normalize(synth.pan_stereo(rumble * level ** 1.5, 0.0))


def click(freq: float, sr: int) -> np.ndarray:
    m = int(0.06 * sr)
    t = np.arange(m) / sr
    buzz = np.sign(np.sin(2 * np.pi * freq * t)) * np.exp(-60 * t)
    return buzz + 0.5 * synth.band_noise(m, 2000, min(6000, sr / 2.2), sr, seed=int(freq)) * np.exp(-90 * t)


def crackle(f, ctx) -> np.ndarray:
    grid = f.arrays["grid"]
    out = np.zeros((ctx.n_samples, 2))
    rows, cols = grid.shape[1:]
    notes = instruments.scale_notes(62, 24)[::-1]           # north row highest
    for k in range(1, f.n_frames):
        rise = grid[k] - grid[k - 1]
        idx = np.argsort(rise, axis=None)[::-1][:CRACKLES_PER_FRAME]
        for flat in idx:
            r, c = divmod(int(flat), cols)
            if rise[r, c] < CRACKLE_RISE:
                break
            midi = notes[int(r * (len(notes) - 1) / (rows - 1))]
            pan = 2 * (c + 0.5) / cols - 1
            synth.add_at(out, synth.pan_stereo(click(mapping.midi_to_hz(midi), ctx.sr) * grid[k, r, c], pan),
                         k / f.fps, ctx.sr)
    return synth.normalize(out)


def region(f, name: str, ctx) -> np.ndarray:
    inst, low, pan = REGIONS[name]
    notes = instruments.scale_notes(low, RANGE_SEMITONES)
    v = f.table[name].rolling(SMOOTH, center=True, min_periods=1).mean().to_numpy(float)
    rank = instruments.ranks(v)
    level = np.clip(v / (np.percentile(v, 98) or 1), 0, 1)
    out = np.zeros((ctx.n_samples, 2))
    t = 0.0
    while t < ctx.duration:
        k = min(int(t * f.fps), f.n_frames - 1)
        if level[k] > 0.05:
            y = instruments.tone(inst, mapping.midi_to_hz(notes[int(round(rank[k] * (len(notes) - 1)))]),
                                 BEAT_S, ctx.sr)
            synth.add_at(out, synth.pan_stereo(y * (0.3 + 0.7 * level[k]), pan), t, ctx.sr)
        t += BEAT_S
    return synth.normalize(out)


def render(ctx):
    f = ctx.page_features()
    stems = {"seasons": seasons(f, ctx), "thunder": thunder(f, ctx), "crackle": crackle(f, ctx)}
    for name in REGIONS:
        stems[name] = region(f, name, ctx)
    return stems
