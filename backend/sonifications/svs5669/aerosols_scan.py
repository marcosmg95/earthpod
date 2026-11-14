"""SVS 5669 (GEOS Aerosols, still map of 19 Aug 2025) — a left-to-right scan, one instrument per aerosol type.

The explorer shows the image with a scan line that crosses it in 48 s (west to east, 180°W -> 180°E).

Background (has its own meaning, always there):
    air     soft wind noise: louder where the column holds more aerosol of any kind
    meridians  a quiet tick every 30° of longitude, a deeper one at 0° (Greenwich) — where you are on the map
Foreground: four instruments, one per aerosol colour, each playing when its colour is in the scanned strip.
    pitch   = latitude of that colour in the strip (north high), on the shared D minor pentatonic
    loudness = how much of the strip is that colour (relative to that type's busiest strip)
    sulfate vibraphone (struck), dust marimba (struck), black carbon cello (held), sea salt flute (held)
Pan follows the scan line: west on the left, east on the right.

Stem script: every layer has a live level slider (STEMS); the rest of PARAMS needs a re-render.
Iterate: uv run python -m jukebox.preview aerosols_scan --start 18 --end 30 --watch
"""
import numpy as np

from jukebox import instruments, mapping, synth
from jukebox.pages import svs5669 as page

TITLE = "Aerosols: four instruments scan the map"
DESCRIPTION = (
    "A scan line crosses NASA SVS 5669's GEOS aerosol map (19 Aug 2025) from west to east in 48 seconds; the sound "
    "moves from left to right with it. Background: a soft wind, louder where there are more aerosols of any kind, "
    "and a quiet tick every 30 degrees of longitude (a deeper one at Greenwich). Foreground: one instrument per "
    "aerosol colour — sulfate (green) vibraphone, dust (lilac) marimba, black carbon / smoke (red-orange) cello, "
    "sea salt (grey-teal) flute. Higher note = further north; louder = more of that colour in the strip. "
    "Listen for the dust marimba over the Atlantic and North Africa, the smoke cello over central Africa, and the "
    "sea-salt flute low in the Southern Ocean. Data: colours measured from the GEOS model image (picture indices, "
    "not aerosol mass).")

AIR_GAIN = 0.25
TICK_GAIN = 0.35
SULFATE_GAIN = 0.45
DUST_GAIN = 0.55
BLACK_CARBON_GAIN = 0.45
SEA_SALT_GAIN = 0.35
OUTPUT_GAIN = 1.0

BEAT_STEPS = 2              # struck notes every 2 scan steps (0.2 s, 1.5 degrees of longitude)
HOLD_STEPS = 5              # held notes last 5 scan steps (0.5 s)
THRESHOLD = 0.08            # a type plays only where it is above this share of its busiest strip
LAT_LOW, LAT_HIGH = -65.0, 70.0   # latitudes at the bottom / top of each instrument's range
RANGE_SEMITONES = 19
PAN_WIDTH = 0.9

STEMS = {"air": "AIR_GAIN", "meridians": "TICK_GAIN", "sulfate": "SULFATE_GAIN", "dust": "DUST_GAIN",
         "black_carbon": "BLACK_CARBON_GAIN", "sea_salt": "SEA_SALT_GAIN"}
PARAMS = {"AIR_GAIN": (0.0, 1.0), "TICK_GAIN": (0.0, 1.0), "SULFATE_GAIN": (0.0, 1.0), "DUST_GAIN": (0.0, 1.0),
          "BLACK_CARBON_GAIN": (0.0, 1.0), "SEA_SALT_GAIN": (0.0, 1.0), "OUTPUT_GAIN": (0.0, 1.5),
          "BEAT_STEPS": (1, 6), "HOLD_STEPS": (2, 12), "THRESHOLD": (0.0, 0.5), "RANGE_SEMITONES": (7, 30),
          "PAN_WIDTH": (0.0, 1.0)}

# aerosol type -> instrument, lowest MIDI note (D minor pentatonic)
VOICES = {"sulfate": ("vibraphone", 62), "dust": ("marimba", 57), "black_carbon": ("cello", 45),
          "sea_salt": ("flute", 69)}


def pan_at(step) -> np.ndarray:
    return PAN_WIDTH * (2 * (np.asarray(step) + 0.5) / page.STEPS - 1)


def note_for(lat: float, low: int) -> int:
    notes = instruments.scale_notes(low, RANGE_SEMITONES)
    pos = np.clip((lat - LAT_LOW) / (LAT_HIGH - LAT_LOW), 0, 1)
    return notes[int(round(pos * (len(notes) - 1)))]


def voice(f, name: str, ctx) -> np.ndarray:
    inst, low = VOICES[name]
    amount = f.table[name].to_numpy(float)
    lat = f.table[f"{name}_lat"].to_numpy(float)
    ref = np.percentile(amount, 98) or 1.0
    step = BEAT_STEPS if instruments.is_struck(inst) else HOLD_STEPS
    out = np.zeros((ctx.n_samples, 2))
    for k in range(0, len(amount), step):
        a = float(amount[k:k + step].mean()) / ref
        if a < THRESHOLD:
            continue
        w = amount[k:k + step]
        la = float((lat[k:k + step] * w).sum() / w.sum()) if w.sum() else float(lat[k])
        dur = step / f.fps
        y = instruments.tone(inst, mapping.midi_to_hz(note_for(la, low)), dur * 1.1, ctx.sr)
        synth.add_at(out, synth.pan_stereo(y * min(1.0, a) ** 0.7, float(pan_at(k + step / 2))), k / f.fps, ctx.sr)
    return synth.normalize(out)


def air(f, ctx) -> np.ndarray:
    total = sum(f.table[t].to_numpy(float) for t in page.TYPES)
    level = np.sqrt(np.clip(total / (np.percentile(total, 98) or 1), 0, 1.2))
    n = ctx.n_samples
    noise = synth.band_noise(n, 250, 2500 if ctx.sr > 8000 else ctx.sr / 2.5, ctx.sr, seed=5669)
    pan = np.interp(np.arange(n) / ctx.sr * f.fps, np.arange(f.n_frames), pan_at(np.arange(f.n_frames)))
    return synth.normalize(synth.pan_stereo(noise * f.per_sample(level, n, ctx.sr, smooth=7), pan))


def meridians(f, ctx) -> np.ndarray:
    out = np.zeros((ctx.n_samples, 2))
    lon = f.table.lon.to_numpy(float)
    for lon_tick in range(-150, 181, 30):
        k = int(np.argmin(np.abs(lon - lon_tick))) if lon_tick < 180 else f.n_frames - 1
        deep = lon_tick == 0
        y = instruments.tone("marimba", mapping.midi_to_hz(38 if deep else 74), 0.3, ctx.sr) * (1.0 if deep else 0.5)
        synth.add_at(out, synth.pan_stereo(y, float(pan_at(k))), k / f.fps, ctx.sr)
    return synth.normalize(out)


def render(ctx):
    f = ctx.page_features()
    stems = {"air": air(f, ctx), "meridians": meridians(f, ctx)}
    for name in VOICES:
        stems[name] = voice(f, name, ctx)
    return stems
