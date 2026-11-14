"""SVS 5533 (Air Quality Model Runs, GEOS-CF, EIC 32:9) — a quartet, one instrument per pollutant panel.

Background (has its own meaning, always there):
    haze    a low drone of two close tones: the more polluted the whole strip looks (mean of the four indices),
            the faster they beat against each other — clean air is a calm tone, dirty air a rough one
    panels  each time a new panel slides into the middle of the screen, its pollutant's short call sign:
            CO two low knocks, PM2.5 a quick grain, NOx a two-note reed, O3 a rising chime
Foreground: one voice per pollutant, panned to where that pollutant is concentrated on screen.
    pitch    = latitude of its darkest areas (north high), on the shared D minor pentatonic
    loudness = its concentration index, relative to its own range in this movie
    accents  = a bell on top when that pollutant's darkest plume is among the darkest of the movie
    CO cello (held), PM2.5 marimba (struck, eighths), NOx oboe (held), O3 flute (held)

Stem script: every layer has a live level slider (STEMS); the rest of PARAMS needs a re-render.
Iterate: uv run python -m jukebox.preview pollutant_quartet --start 0 --end 15 --watch
"""
import numpy as np

from jukebox import instruments, mapping, synth
from jukebox.pages import svs5533 as page

TITLE = "Air quality: a pollutant quartet"
DESCRIPTION = (
    "NASA SVS 5533 shows four pollutants side by side in panels that drift across the screen. Background: a low "
    "drone that beats faster and rougher the more polluted the whole strip looks, and a short call sign each time a "
    "new panel reaches the middle of the screen (carbon monoxide: two low knocks; fine particles: a quick grain; "
    "nitrogen oxides: a two-note reed; ozone: a rising chime). Foreground: one instrument per pollutant, heard "
    "where it is on screen — carbon monoxide cello, fine particles marimba, nitrogen oxides oboe, ozone flute. "
    "Higher note = its darkest areas are further north; louder = higher concentration (relative to that "
    "pollutant's range in this movie); a bell marks its darkest plumes. Data: colours measured from the GEOS-CF "
    "model movie (darker = more, per each panel's colour scale); picture indices, not ppb or micrograms.")

HAZE_GAIN = 0.20
PANELS_GAIN = 0.30
CO_GAIN = 0.40
PM25_GAIN = 0.45
NOX_GAIN = 0.35
O3_GAIN = 0.30
OUTPUT_GAIN = 1.0

BEAT_S = 0.5                # held notes per beat; struck PM2.5 plays two per beat
RANGE_SEMITONES = 12
LAT_LOW, LAT_HIGH = -20.0, 55.0
ACCENT_PCT = 92             # bell when the pollutant's peak darkness is above this percentile of the movie
BEAT_MIN, BEAT_MAX = 0.3, 7.0   # haze beating (Hz) for the cleanest / dirtiest strip
PAN_WIDTH = 0.9

STEMS = {"haze": "HAZE_GAIN", "panels": "PANELS_GAIN", "co": "CO_GAIN", "pm25": "PM25_GAIN",
         "nox": "NOX_GAIN", "o3": "O3_GAIN"}
PARAMS = {"HAZE_GAIN": (0.0, 1.0), "PANELS_GAIN": (0.0, 1.0), "CO_GAIN": (0.0, 1.0), "PM25_GAIN": (0.0, 1.0),
          "NOX_GAIN": (0.0, 1.0), "O3_GAIN": (0.0, 1.0), "OUTPUT_GAIN": (0.0, 1.5),
          "BEAT_S": (0.2, 1.5), "RANGE_SEMITONES": (5, 24), "ACCENT_PCT": (50, 100),
          "BEAT_MIN": (0.0, 3.0), "BEAT_MAX": (1.0, 15.0), "PAN_WIDTH": (0.0, 1.0)}

# pollutant -> instrument, lowest MIDI note
VOICES = {"co": ("cello", 43), "pm25": ("marimba", 62), "nox": ("oboe", 57), "o3": ("flute", 69)}
# call signs: (instrument, [(offset s, midi)])
CALLS = {"co": ("marimba", [(0.0, 38), (0.12, 38)]), "pm25": ("harp", [(0.0, 86)]),
         "nox": ("oboe", [(0.0, 62), (0.12, 67)]), "o3": ("vibraphone", [(0.0, 74), (0.09, 81)])}


def rel(v: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(v, 2), np.percentile(v, 98)
    return np.clip((v - lo) / max(hi - lo, 1e-9), 0, 1)


def voice(f, p: str, ctx) -> np.ndarray:
    inst, low = VOICES[p]
    notes = instruments.scale_notes(low, RANGE_SEMITONES)
    level, lat = rel(f.table[p].to_numpy(float)), f.table[f"{p}_lat"].to_numpy(float)
    x = f.table[f"{p}_x"].to_numpy(float)
    peak = f.table[f"{p}_peak"].to_numpy(float)
    accent_from = np.percentile(peak, ACCENT_PCT)
    step = BEAT_S / 2 if instruments.is_struck(inst) else BEAT_S
    out = np.zeros((ctx.n_samples, 2))
    t, last_accent = 0.0, -10.0
    while t < ctx.duration:
        a, b = int(t * f.fps), min(int((t + step) * f.fps), f.n_frames)
        if b <= a:
            break
        lv = float(level[a:b].mean())
        pos = np.clip((float(lat[a:b].mean()) - LAT_LOW) / (LAT_HIGH - LAT_LOW), 0, 1)
        midi = notes[int(round(pos * (len(notes) - 1)))]
        pan = PAN_WIDTH * (2 * float(x[a:b].mean()) - 1)
        y = instruments.tone(inst, mapping.midi_to_hz(midi), step * 1.05, ctx.sr) * (0.1 + 0.9 * lv)
        synth.add_at(out, synth.pan_stereo(y, pan), t, ctx.sr)
        if peak[a:b].max() >= accent_from and t - last_accent > 1.0:
            bell = synth.tone(mapping.midi_to_hz(midi + 12), 1.2, "bell", ctx.sr) * 0.35
            synth.add_at(out, synth.pan_stereo(bell, pan), t, ctx.sr)
            last_accent = t
        t += step
    return synth.normalize(out)


def haze(f, ctx) -> np.ndarray:
    n, sr = ctx.n_samples, ctx.sr
    dirt = rel(sum(f.table[p].to_numpy(float) for p in page.POLLUTANTS))
    beat = f.per_sample(BEAT_MIN + (BEAT_MAX - BEAT_MIN) * dirt, n, sr, smooth=31)
    f0 = mapping.midi_to_hz(38)
    t = np.arange(n) / sr
    y = np.sin(2 * np.pi * f0 * t) + np.sin(2 * np.pi * np.cumsum(f0 + beat) / sr)
    y += 0.3 * (np.sin(4 * np.pi * f0 * t) + np.sin(4 * np.pi * np.cumsum(f0 + beat) / sr))
    return synth.normalize(synth.pan_stereo(y, 0.0))


def panels(f, ctx) -> np.ndarray:
    out = np.zeros((ctx.n_samples, 2))
    centre = f.table.centre.tolist()
    for k in range(1, f.n_frames):
        if centre[k] != centre[k - 1] and all(c == centre[k] for c in centre[k:k + 6]):  # settled change
            inst, figure = CALLS[centre[k]]
            for dt, midi in figure:
                y = instruments.tone(inst, mapping.midi_to_hz(midi), 0.25, ctx.sr) * 0.8
                synth.add_at(out, synth.pan_stereo(y, 0.0), k / f.fps + dt, ctx.sr)
    return synth.normalize(out)


def render(ctx):
    f = ctx.page_features()
    stems = {"haze": haze(f, ctx), "panels": panels(f, ctx)}
    for p in VOICES:
        stems[p] = voice(f, p, ctx)
    return stems
