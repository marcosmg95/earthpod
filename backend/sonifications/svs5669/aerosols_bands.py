"""SVS 5669 (GEOS Aerosols, still map of 19 Aug 2025) — latitude bands + automatically found plumes.

A rework of aerosols_scan with one fixed rule for every aerosol type (Hermann's criteria: the sound comes only
from the measured grid, by a rule that is the same everywhere, and works on any map drawn with this legend).

The scan line crosses the map west to east in 48 s; pan follows it (west left, east right).

    pitch      = latitude band (10 degrees each, north high), one fixed note per band on the D minor
                 pentatonic, the SAME for all four types: a strip with aerosol at two latitudes sounds as two
                 notes, never as one averaged note
    loudness   = how far that type is ABOVE ITS USUAL LEVEL in that band (the band's median over all
                 longitudes), on ONE scale shared by all types: the background haze stays quiet, and a thick
                 plume is louder than a thin one whatever its type
    timbre     = type (a fixed legend): sulfate = smooth hum, sea salt = surf (narrow noise),
                 dust = sand grains (more grains = more dust), black carbon / smoke = crackle
Layers:
    haze       soft wind noise: total amount of all four colours in the strip (not above-usual)
    meridians  a tick every 30 degrees of longitude, a deeper one at Greenwich
    stops      a glass chime where the scan enters one of the N_STOPS biggest plumes. Plumes are found in
               the grid, not chosen by hand: connected cells of one type above STOP_LEVEL, ranked by area-
               weighted size; chime pitch = the plume's centre band, loudness = its size
Data: picture indices of the GEOS image (colour amounts), not aerosol mass. The scan cannot show motion: a
still has no wind, so nothing here suggests a direction of travel.

Iterate: uv run python -m jukebox.preview aerosols_bands --start 12 --end 30 --watch
"""
import numpy as np

from jukebox import instruments, mapping, synth
from jukebox.pages import svs5669 as page

TITLE = "Aerosols: latitude bands and plumes (systematic)"
DESCRIPTION = (
    "A scan line crosses NASA SVS 5669's GEOS aerosol map (19 Aug 2025) from west to east in 48 seconds, and the "
    "sound pans with it. Every 10-degree band of latitude has its own note (north high), the same for all aerosol "
    "types, so plumes at different latitudes sound as different notes at once. Each type has its own sound: "
    "sulfate a smooth hum, sea salt surf, dust sand grains, smoke (black carbon) a crackle. Loudness means how far "
    "a type is above its usual level for that latitude, on one scale for all types, so the everyday haze stays "
    "quiet and big plumes stand out. A glass chime marks the start of each of the largest plumes, found "
    "automatically in the image. Underneath: a soft wind for the total amount of aerosol, and a tick every 30 "
    "degrees of longitude. Data: colours measured from the GEOS Forward Processing image by NASA GMAO / SVS "
    "(picture indices, not aerosol mass).")

HAZE_GAIN = 0.2
TICK_GAIN = 0.3
STOP_GAIN = 0.5
SULFATE_GAIN = 0.6
DUST_GAIN = 0.7
BLACK_CARBON_GAIN = 0.7
SEA_SALT_GAIN = 0.6
OUTPUT_GAIN = 1.0

BAND_ROWS = 2               # measured rows (5 degrees) per band -> 10-degree bands
LOW_MIDI = 45               # note of the southernmost band; each band north is the next pentatonic note
BASELINE_PCT = 50           # "usual level" of a type in a band = this percentile over all longitudes
SCALE_PCT = 99.5            # shared loudness scale: this percentile of all types' above-usual amounts = 1
FLOOR = 0.10               # below this share of the shared scale a band is silent
GRAIN_RATE = 80.0           # dust grains per second in a band at full level
CRACKLE_RATE = 60.0         # smoke crackles per second in a band at full level
N_STOPS = 6
STOP_LEVEL = 0.25           # a plume = connected cells of one type above this level (shared scale)
PAN_WIDTH = 0.9

STEMS = {"haze": "HAZE_GAIN", "meridians": "TICK_GAIN", "stops": "STOP_GAIN", "sulfate": "SULFATE_GAIN",
         "dust": "DUST_GAIN", "black_carbon": "BLACK_CARBON_GAIN", "sea_salt": "SEA_SALT_GAIN"}
PARAMS = {"HAZE_GAIN": (0.0, 1.0), "TICK_GAIN": (0.0, 1.0), "STOP_GAIN": (0.0, 1.0), "SULFATE_GAIN": (0.0, 1.0),
          "DUST_GAIN": (0.0, 1.0), "BLACK_CARBON_GAIN": (0.0, 1.0), "SEA_SALT_GAIN": (0.0, 1.0),
          "OUTPUT_GAIN": (0.0, 1.5), "BASELINE_PCT": (0, 90), "SCALE_PCT": (90.0, 100.0), "FLOOR": (0.0, 0.3),
          "GRAIN_RATE": (10.0, 200.0), "CRACKLE_RATE": (10.0, 200.0), "N_STOPS": (0, 12),
          "STOP_LEVEL": (0.05, 0.8), "PAN_WIDTH": (0.0, 1.0)}


# ---- the mapping (pure functions of the measured grid) ------------------------------------------------------

def band_lats(rows: int) -> np.ndarray:
    """Centre latitude of each band, north first."""
    n = rows // BAND_ROWS
    return 90 - (np.arange(n) + 0.5) * 180 / n


def band_midi(n_bands: int) -> list[int]:
    """One pentatonic note per band, the southernmost lowest (index 0 = north, like the grid)."""
    notes = instruments.scale_notes(LOW_MIDI, 60)[:n_bands]
    return notes[::-1]


def levels(arrays: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """type -> (steps, bands) above-usual amount on the shared 0..1 scale."""
    above = {}
    for name in page.TYPES:
        a = np.asarray(arrays[name], float)
        a = a[:, : a.shape[1] - a.shape[1] % BAND_ROWS]
        bands = a.reshape(len(a), -1, BAND_ROWS).mean(axis=2)
        above[name] = np.clip(bands - np.percentile(bands, BASELINE_PCT, axis=0), 0, None)
    pooled = np.concatenate([v.ravel() for v in above.values()])
    scale = np.percentile(pooled[pooled > 0], SCALE_PCT) if (pooled > 0).any() else 1.0
    return {k: np.clip(v / scale, 0, 1) for k, v in above.items()}


def plumes(lv: dict[str, np.ndarray], lats: np.ndarray) -> list[dict]:
    """Connected cells (4-neighbours, wrapping at 180 degrees) of one type above STOP_LEVEL, largest first.

    size = sum of level x cos(latitude) (area-weighted); start/end = first/last scan step it covers.
    """
    found = []
    for name, grid in lv.items():
        on = grid > STOP_LEVEL
        seen = np.zeros_like(on)
        steps, bands = on.shape
        for s0, b0 in zip(*np.nonzero(on)):
            if seen[s0, b0]:
                continue
            seen[s0, b0] = True
            stack, cells = [(s0, b0)], []
            while stack:
                s, b = stack.pop()
                cells.append((s, b))
                for ds, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    t, c = (s + ds) % steps, b + db
                    if 0 <= c < bands and on[t, c] and not seen[t, c]:
                        seen[t, c] = True
                        stack.append((t, c))
            s_idx = np.array([c[0] for c in cells])
            b_idx = np.array([c[1] for c in cells])
            w = grid[s_idx, b_idx] * np.cos(np.radians(lats[b_idx]))
            cols = np.unique(s_idx)
            gaps = np.diff(np.concatenate([cols, [cols[0] + steps]]))
            first = int(cols[(np.argmax(gaps) + 1) % len(cols)])          # handles plumes across 180 degrees
            found.append(dict(type=name, size=float(w.sum()), start=first, width=int(len(cols)),
                              lat=float((lats[b_idx] * w).sum() / w.sum()),
                              band=int(round((b_idx * w).sum() / w.sum()))))
    return sorted(found, key=lambda p: -p["size"])


def tour(f) -> list[dict]:
    """The stops the chimes mark, in the order the scan reaches them (also used by the tests)."""
    lv = levels(f.arrays)
    lats = band_lats(next(iter(f.arrays.values())).shape[1])
    stops = plumes(lv, lats)[: int(N_STOPS)]
    for p in stops:
        p["lon"] = float(page.lon_of(p["start"]))
    return sorted(stops, key=lambda p: p["start"])


# ---- sounds -----------------------------------------------------------------------------------------------

def pan_at(step) -> np.ndarray:
    return PAN_WIDTH * (2 * (np.asarray(step) + 0.5) / page.STEPS - 1)


def scan_pan(f, n: int, sr: int) -> np.ndarray:
    return np.interp(np.arange(n) / sr * f.fps, np.arange(f.n_frames), pan_at(np.arange(f.n_frames)))


def hum(env: np.ndarray, hz: float, sr: int, band: int) -> np.ndarray:
    t = np.arange(len(env)) / sr
    return (np.sin(2 * np.pi * hz * t) + 0.25 * np.sin(4 * np.pi * hz * t)) * env * 0.8


def surf(env: np.ndarray, hz: float, sr: int, band: int) -> np.ndarray:
    hi = min(hz * 1.12, sr / 2.6)
    return synth.band_noise(len(env), hz * 0.9, hi, sr, seed=5669 + band) * env * 2.4


def events(level: np.ndarray, rate: float, fps: float, rng) -> list[tuple[float, float]]:
    """(time s, level) of random events, `rate` per second at level 1 (Poisson, so density = amount)."""
    out = []
    for k, v in enumerate(level):
        if v < FLOOR:
            continue
        for _ in range(rng.poisson(v * rate / fps)):
            out.append(((k + rng.random()) / fps, float(v)))
    return out


def grains(level, hz, sr, fps, n, seed) -> np.ndarray:
    rng = np.random.default_rng(seed)
    g_n = int(0.03 * sr)
    grain = np.sin(2 * np.pi * hz * np.arange(g_n) / sr) * np.hanning(g_n)
    out = np.zeros(n)
    for t, _ in events(level, GRAIN_RATE, fps, rng):
        i = int(t * sr)
        j = min(n, i + g_n)
        out[i:j] += grain[: j - i] * rng.uniform(0.6, 1.0)
    return out


def crackle(level, hz, sr, fps, n, seed) -> np.ndarray:
    rng = np.random.default_rng(seed)
    c_n = int(0.012 * sr)
    t = np.arange(c_n) / sr
    click = (np.sin(2 * np.pi * hz * 2 * t) + 0.6 * rng.standard_normal(c_n)) * np.exp(-t / 0.0025)
    out = np.zeros(n)
    for when, _ in events(level, CRACKLE_RATE, fps, rng):
        i = int(when * sr)
        j = min(n, i + c_n)
        out[i:j] += 2.5 * click[: j - i] * min(1.0, rng.pareto(3.0) * 0.5 + 0.2)   # a few loud pops, many soft
    return out


def type_stem(f, ctx, name: str, lv: np.ndarray, midis: list[int]) -> np.ndarray:
    n, sr = ctx.n_samples, ctx.sr
    mono = np.zeros(n)
    for b in range(lv.shape[1]):
        col = lv[:, b]
        if col.max() < FLOOR:
            continue
        hz = mapping.midi_to_hz(midis[b])
        seed = 5669 * 100 + 10 * b + page.TYPES.index(name)
        if name == "dust":
            mono += grains(col, hz, sr, f.fps, n, seed)
        elif name == "black_carbon":
            mono += crackle(col, hz, sr, f.fps, n, seed)
        else:
            env = f.per_sample(np.where(col >= FLOOR, col, 0.0), n, sr, smooth=5)
            mono += (hum if name == "sulfate" else surf)(env, hz, sr, b)
    return synth.pan_stereo(mono, scan_pan(f, n, sr))


def haze(f, ctx) -> np.ndarray:
    total = sum(f.table[t].to_numpy(float) for t in page.TYPES)
    level = np.sqrt(np.clip(total / (np.percentile(total, 98) or 1), 0, 1.2))
    n = ctx.n_samples
    noise = synth.band_noise(n, 250, min(2500, ctx.sr / 2.5), ctx.sr, seed=5669)
    return synth.normalize(synth.pan_stereo(noise * f.per_sample(level, n, ctx.sr, smooth=7), scan_pan(f, n, ctx.sr)))


def meridians(f, ctx) -> np.ndarray:
    out = np.zeros((ctx.n_samples, 2))
    lon = f.table.lon.to_numpy(float)
    for lon_tick in range(-150, 181, 30):
        k = int(np.argmin(np.abs(lon - lon_tick))) if lon_tick < 180 else f.n_frames - 1
        deep = lon_tick == 0
        y = instruments.tone("marimba", mapping.midi_to_hz(38 if deep else 74), 0.3, ctx.sr) * (1.0 if deep else 0.5)
        synth.add_at(out, synth.pan_stereo(y, float(pan_at(k))), k / f.fps, ctx.sr)
    return synth.normalize(out)


def chimes(f, ctx, stops: list[dict], midis: list[int]) -> np.ndarray:
    out = np.zeros((ctx.n_samples, 2))
    if not stops:
        return out
    biggest = max(p["size"] for p in stops)
    for p in stops:
        y = instruments.tone("fm_glass", mapping.midi_to_hz(midis[p["band"]] + 12), 1.0, ctx.sr)
        synth.add_at(out, synth.pan_stereo(y * np.sqrt(p["size"] / biggest), float(pan_at(p["start"]))),
                     p["start"] / f.fps, ctx.sr)
    return synth.normalize(out)


def render(ctx):
    f = ctx.page_features()
    lv = levels(f.arrays)
    midis = band_midi(next(iter(lv.values())).shape[1])
    voices = {name: type_stem(f, ctx, name, lv[name], midis) for name in page.TYPES}
    # one scale for all four types (a high percentile, so a few crackle spikes do not turn everything down)
    ref = float(np.percentile(np.abs(np.concatenate(list(voices.values()))), 99.9)) or 1.0
    stems = {name: np.clip(v / ref * 0.8, -1, 1) for name, v in voices.items()}
    stems.update(haze=haze(f, ctx), meridians=meridians(f, ctx), stops=chimes(f, ctx, tour(f), midis))
    return stems
