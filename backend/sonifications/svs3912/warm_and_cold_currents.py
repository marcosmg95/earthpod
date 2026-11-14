"""SVS 3912 (ECCO2 sea surface currents coloured by temperature, flat map) — three oceans and a sweeping radar.

Background (has its own meaning, always there):
    flow     a sea-noise bed: louder while the streaks move more, brighter in tone while the map is warmer
Foreground:
    pacific / atlantic / indian   one instrument per ocean basin, panned to where it is on the map,
             one note per beat: pitch = how warm that basin looks now (ranked over the movie: warmer = higher),
             loudness = how much its streaks are moving. Pacific cello (left), Atlantic flute (centre-left),
             Indian Ocean vibraphone (right).
    sweep    every SWEEP_EVERY_S seconds the map is swept west -> east in SWEEP_S seconds (like
             svs5313/nightlights_three_acts): each 10° column plays its most active cell — pitch = its latitude
             (north high), loudness = its motion, a bell if that water is warm (orange / red), a pluck if cold.

Stem script: every layer has a live level slider (STEMS); the rest of PARAMS needs a re-render.
Iterate: uv run python -m jukebox.preview warm_and_cold --start 10 --end 25 --watch
"""
import numpy as np

from jukebox import instruments, mapping, synth
from jukebox.pages import svs3912 as page

TITLE = "Sea surface currents: three oceans and a radar sweep"
DESCRIPTION = (
    "NASA SVS 3912 shows surface currents as streaks coloured by temperature (blue cold, red warm). Background: a "
    "sea-noise bed, louder while the streaks move more and brighter while the map is warmer. Foreground: one "
    "instrument per ocean — Pacific cello (left), Atlantic flute (centre-left), Indian Ocean vibraphone (right): "
    "higher note = that ocean looks warmer than usual in this movie, louder = its currents move more. Every few "
    "seconds a radar sweep crosses the map west to east: higher note = further north, louder = faster-changing "
    "streaks, bells for warm water and plucks for cold. Data: colours and motion measured from the ECCO2 model "
    "movie (picture indices, not degrees or metres per second). The page gives no dates for the frames.")

FLOW_GAIN = 0.25
PACIFIC_GAIN = 0.40
ATLANTIC_GAIN = 0.35
INDIAN_GAIN = 0.40
SWEEP_GAIN = 0.45
OUTPUT_GAIN = 1.0

BEAT_S = 0.5
SWEEP_EVERY_S = 8.0
SWEEP_S = 2.5
WARM = 0.72                 # temperature index above which a swept cell rings as a bell
RANGE_SEMITONES = 12
SMOOTH = 15

STEMS = {"flow": "FLOW_GAIN", "pacific": "PACIFIC_GAIN", "atlantic": "ATLANTIC_GAIN", "indian": "INDIAN_GAIN",
         "sweep": "SWEEP_GAIN"}
PARAMS = {"FLOW_GAIN": (0.0, 1.0), "PACIFIC_GAIN": (0.0, 1.0), "ATLANTIC_GAIN": (0.0, 1.0),
          "INDIAN_GAIN": (0.0, 1.0), "SWEEP_GAIN": (0.0, 1.0), "OUTPUT_GAIN": (0.0, 1.5),
          "BEAT_S": (0.2, 1.5), "SWEEP_EVERY_S": (3.0, 30.0), "SWEEP_S": (0.5, 6.0), "WARM": (0.4, 0.95),
          "RANGE_SEMITONES": (5, 24), "SMOOTH": (1, 60)}

BASINS = {"pacific": ("cello", 45, -0.85), "atlantic": ("flute", 69, -0.2), "indian": ("vibraphone", 62, 0.5)}


def rel(v: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(v, 2), np.percentile(v, 98)
    return np.clip((v - lo) / max(hi - lo, 1e-9), 0, 1)


def flow(f, ctx) -> np.ndarray:
    n, sr = ctx.n_samples, ctx.sr
    motion = f.per_sample(rel(f.table.motion.to_numpy(float)), n, sr, SMOOTH)
    warm = f.per_sample(rel(f.table.temp.to_numpy(float)), n, sr, SMOOTH * 4)
    hi = min(5000, sr / 2.5)
    dull, bright = synth.band_noise(n, 80, 700, sr, seed=3912), synth.band_noise(n, 400, hi, sr, seed=3913)
    y = ((1 - warm) * dull + warm * bright) * (0.2 + 0.8 * motion)
    return synth.normalize(synth.pan_stereo(y, 0.0))


def basin(f, name: str, ctx) -> np.ndarray:
    inst, low, pan = BASINS[name]
    notes = instruments.scale_notes(low, RANGE_SEMITONES)
    temp = f.table[f"{name}_temp"].rolling(SMOOTH, center=True, min_periods=1).mean().to_numpy(float)
    move = rel(f.table[f"{name}_motion"].rolling(SMOOTH, center=True, min_periods=1).mean().to_numpy(float))
    rank = instruments.ranks(temp)
    out = np.zeros((ctx.n_samples, 2))
    t = 0.0
    while t < ctx.duration:
        k = min(int(t * f.fps), f.n_frames - 1)
        m = notes[int(round(rank[k] * (len(notes) - 1)))]
        y = instruments.tone(inst, mapping.midi_to_hz(m), BEAT_S * 1.05, ctx.sr) * (0.15 + 0.85 * move[k])
        synth.add_at(out, synth.pan_stereo(y, pan), t, ctx.sr)
        t += BEAT_S
    return synth.normalize(out)


def sweep(f, ctx) -> np.ndarray:
    temp, motion = f.arrays["temp"], f.arrays["motion"]
    rows, cols = temp.shape[1:]
    notes = instruments.scale_notes(50, 24)[::-1]            # row 0 (north) highest
    ref = np.percentile(motion.max(axis=1), 95) or 1.0
    out = np.zeros((ctx.n_samples, 2))
    t0 = 1.0
    while t0 + SWEEP_S <= ctx.duration:
        k = min(int(t0 * f.fps), f.n_frames - 1)
        for c in range(cols):
            r = int(motion[k, :, c].argmax())
            level = min(1.0, motion[k, r, c] / ref)
            if level < 0.05:
                continue
            m = notes[int(r * (len(notes) - 1) / (rows - 1))]
            hz = mapping.midi_to_hz(m)
            y = synth.tone(hz, 0.6, "bell", ctx.sr) * 0.6 if temp[k, r, c] >= WARM else synth.tone(hz, 0.4, "pluck", ctx.sr)
            synth.add_at(out, synth.pan_stereo(y * level, 2 * (c + 0.5) / cols - 1), t0 + SWEEP_S * c / cols, ctx.sr)
        t0 += SWEEP_EVERY_S
    return synth.normalize(out)


def render(ctx):
    f = ctx.page_features()
    stems = {"flow": flow(f, ctx), "sweep": sweep(f, ctx)}
    for name in BASINS:
        stems[name] = basin(f, name, ctx)
    return stems
