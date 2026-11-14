"""SVS 5196 (DYAMOND global CO2) — breathing, a heartbeat, and one instrument per region.

Background (has its own meaning, always there):
    breath     tan haze on screen (loudness = amount, brightness = rising / falling)
    heart      co2_13_heartbeat_improved.py (daily orange-red pulse, panned by its screen position)
Foreground: six instruments, entering in pairs as the orbiting camera brings each pair of regions into view.
The globe turns westward, so the order is Asia + Oceania, then Europe + Africa, then the Americas.

Rules that keep the six voices apart (each pair = one sustained + one struck/plucked voice):
    register follows latitude (north higher), pan follows longitude (west left, east right),
    every voice uses the same D minor pentatonic (any combination is consonant; data picks scale degrees),
    sustained voices play half notes, struck voices eighths, locked to the heartbeat (1 model day = 1 beat).

Stem script: every layer has a live level slider (STEMS); everything else in PARAMS needs a re-render.
Iterate: uv run python -m jukebox.preview co2_15 --start 8 --end 16 --watch --set PAIR2_IN=10.5
"""
from pathlib import Path

import numpy as np

from jukebox import mapping, sonify, synth

TITLE = "Living Earth: lungs, heartbeat and regions"
DESCRIPTION = ("Background: a centred soft breath (more tan haze on screen = louder; brighter while the haze grows, "
               "darker while it fades) and the CO2 heartbeat (daily pulse of the orange-red area, panned by its "
               "position). Foreground: one instrument per region, entering in pairs as the orbit brings it into view "
               "(Asia oboe + Oceania harp, Europe flute + Africa marimba, North America vibraphone + South America "
               "cello). Higher register = further north, left/right = west/east. Each instrument's pitch is the "
               "orange-red amount in its part of the screen (upper third for the northern region, lower two thirds "
               "for the southern one), ranked against that pair's time on screen (higher note = more than usual "
               "for that stretch). Timed for the orbit movie. Data: "
               "colours measured from the NASA SVS 5196 movie (GEOS / DYAMOND model), not actual breathing, a "
               "heartbeat or CO2 in ppm; camera and background affect these picture indices.")

# ---- mix (live sliders: no re-render) ----------------------------------------------------------------
BREATH_GAIN = 0.07
HEART_GAIN = 1.0
ASIA_GAIN = 0.30            # oboe
OCEANIA_GAIN = 0.40         # harp
EUROPE_GAIN = 0.28          # flute
AFRICA_GAIN = 0.40          # marimba
NORTH_AMERICA_GAIN = 0.35   # vibraphone
SOUTH_AMERICA_GAIN = 0.30   # cello
OUTPUT_GAIN = 1.0

# ---- when each pair is on screen (seconds of movie; orbit camera) -------------------------------------
PAIR1_IN, PAIR1_OUT = 0.0, 13.0     # Asia + Oceania
PAIR2_IN, PAIR2_OUT = 9.5, 30.0     # Europe + Africa
PAIR3_IN, PAIR3_OUT = 23.0, 40.0    # North + South America (out past the end = plays to the end)
FADE_S = 1.5                        # fade in / out of each pair

# ---- melody ------------------------------------------------------------------------------------------
DAY_FRAMES = 24             # one model day (1 frame = 1 hour): one beat, the heartbeat's own period
STRUCK_SUBDIV = 2           # struck notes per beat (2 = eighths)
SUSTAIN_BEATS = 2           # beats per sustained note (2 = half notes)
RANGE_SEMITONES = 12        # each voice spans this much above its lowest note
MELODY_SMOOTH_FRAMES = 6    # rolling mean of the data before it picks notes (larger = calmer melodies)
REST_BELOW = 0.10           # struck voices rest when their data is in the bottom part of its range (0 = never)
ACCENT = 0.70               # level of off-beat struck notes (1 = no accent)
PAN_WIDTH = 1.0             # 0 = all centred, 1 = the longitude pans below
DUCK_DB = 4.5               # breath drops this much while instruments play

# ---- breath (background) -----------------------------------------------------------------------------
INHALE_BAND = (300, 900)
EXHALE_BAND = (180, 500)
FLOW_BAND = (80, 260)
INHALE_W, FLOW_W = 0.65, 0.18
BREATH_SMOOTH_FRAMES = 5
SLOPE_SENS = 3.0            # how quickly the breath swings fully to inhale / exhale
LEVEL_EXP = 0.5             # loudness curve of the haze (0.5 = square root; 1 = linear; 2 = exaggerated)

STEMS = {"breath": "BREATH_GAIN", "heart": "HEART_GAIN",
         "asia": "ASIA_GAIN", "oceania": "OCEANIA_GAIN", "europe": "EUROPE_GAIN", "africa": "AFRICA_GAIN",
         "north_america": "NORTH_AMERICA_GAIN", "south_america": "SOUTH_AMERICA_GAIN"}

PARAMS = {
    # levels (live)
    "BREATH_GAIN": (0.0, 0.5), "HEART_GAIN": (0.0, 1.5),
    "ASIA_GAIN": (0.0, 1.0), "OCEANIA_GAIN": (0.0, 1.0), "EUROPE_GAIN": (0.0, 1.0),
    "AFRICA_GAIN": (0.0, 1.0), "NORTH_AMERICA_GAIN": (0.0, 1.0), "SOUTH_AMERICA_GAIN": (0.0, 1.0),
    "OUTPUT_GAIN": (0.0, 1.5),
    # entries
    "PAIR1_IN": (0.0, 40.0), "PAIR1_OUT": (0.0, 40.0), "PAIR2_IN": (0.0, 40.0), "PAIR2_OUT": (0.0, 40.0),
    "PAIR3_IN": (0.0, 40.0), "PAIR3_OUT": (0.0, 40.0), "FADE_S": (0.1, 5.0),
    # melody
    "STRUCK_SUBDIV": (1, 4), "SUSTAIN_BEATS": (1, 4), "RANGE_SEMITONES": (5, 24),
    "MELODY_SMOOTH_FRAMES": (1, 24), "REST_BELOW": (0.0, 0.6), "ACCENT": (0.3, 1.0),
    "PAN_WIDTH": (0.0, 1.2), "DUCK_DB": (0.0, 12.0),
    # breath
    "SLOPE_SENS": (0.5, 8.0), "LEVEL_EXP": (0.2, 2.0), "BREATH_SMOOTH_FRAMES": (1, 24),
}

# Region -> pair, instrument, lowest note (MIDI, in D minor pentatonic), pan (longitude), data columns.
REGIONS = {
    "asia":          dict(pair=1, inst="oboe",       low=67, pan=+0.60, cols=("top",)),          # G4 ~35N
    "oceania":       dict(pair=1, inst="harp",       low=50, pan=+0.85, cols=("mid", "bottom")),  # D3 ~25S
    "europe":        dict(pair=2, inst="flute",      low=74, pan=+0.00, cols=("top",)),          # D5 ~50N
    "africa":        dict(pair=2, inst="marimba",    low=62, pan=+0.10, cols=("mid", "bottom")),  # D4 ~5N
    "north_america": dict(pair=3, inst="vibraphone", low=69, pan=-0.70, cols=("top",)),          # A4 ~45N
    "south_america": dict(pair=3, inst="cello",      low=57, pan=-0.50, cols=("mid", "bottom")),  # A3 ~15S
}

# Additive instrument models: partials (ratio, amplitude, decay 1/s; 0 = held), attack / release (s),
# ring = length of a struck note (s), vib = (rate Hz, depth), trem = (rate Hz, depth), breath = air noise level.
INSTRUMENTS = {
    "vibraphone": dict(struck=True, ring=2.6, attack=0.003, release=0.25, trem=(5.5, 0.30),
                       parts=[(1, 1.0, 0.9), (4, 0.30, 3.0), (10, 0.06, 9.0)]),
    "marimba":    dict(struck=True, ring=0.7, attack=0.002, release=0.05,
                       parts=[(1, 1.0, 5.0), (4, 0.35, 16.0), (9.9, 0.08, 40.0)]),
    "harp":       dict(struck=True, ring=1.8, attack=0.004, release=0.20,
                       parts=[(k, 1 / k ** 1.4, 1.2 + 0.9 * k) for k in range(1, 9)]),
    "cello":      dict(struck=False, attack=0.18, release=0.35, vib=(5.0, 0.004),
                       parts=[(k, 1 / k ** 1.3 * (1.3 if k in (2, 3) else 1.0), 0) for k in range(1, 11)]),
    "flute":      dict(struck=False, attack=0.09, release=0.25, vib=(5.0, 0.003), breath=0.05,
                       parts=[(1, 1.0, 0), (2, 0.22, 0), (3, 0.08, 0)]),
    "oboe":       dict(struck=False, attack=0.05, release=0.18, vib=(5.5, 0.003),
                       parts=[(1, 0.45, 0), (2, 1.0, 0), (3, 0.80, 0), (4, 0.55, 0), (5, 0.35, 0),
                              (6, 0.20, 0), (7, 0.12, 0)]),
}


def instrument_tone(inst: str, freq: float, dur: float, sr: int) -> np.ndarray:
    """One note of an instrument model, mono, `dur` seconds (struck notes ring for their own `ring`)."""
    spec = INSTRUMENTS[inst]
    n = max(1, int((spec["ring"] if spec["struck"] else dur) * sr))
    t = np.arange(n) / sr
    rate, depth = spec.get("vib", (0.0, 0.0))
    phase = 2 * np.pi * freq * np.cumsum(1 + depth * np.sin(2 * np.pi * rate * t)) / sr
    y = sum(a * np.sin(k * phase) * (np.exp(-d * t) if d else 1.0)
            for k, a, d in spec["parts"] if freq * k < sr / 2)
    if spec.get("breath"):
        y = y + spec["breath"] * synth.band_noise(n, 1500, 5000, sr, seed=94)
    env = np.minimum(1.0, t / spec["attack"])
    rel = min(n, int(spec["release"] * sr))
    if rel:
        env[-rel:] *= np.linspace(1, 0, rel)
    if "trem" in spec:
        r, d = spec["trem"]
        env *= 1 - d * (0.5 - 0.5 * np.cos(2 * np.pi * r * t))
    return y * env


def scale_notes(low: int) -> list[int]:
    """MIDI notes of the shared D minor pentatonic from `low` to `low + RANGE_SEMITONES`."""
    return [m for m in range(low, low + RANGE_SEMITONES + 1) if (m - mapping.TONIC_MIDI) % 12 in mapping.SCALE]


def window(n: int, sr: int, t_in: float, t_out: float) -> np.ndarray:
    """0..1 per sample: smooth fade in after t_in, fade out before t_out."""
    t = np.arange(n) / sr
    up = np.clip((t - t_in) / FADE_S, 0, 1)
    down = np.clip((t_out - t) / FADE_S, 0, 1)
    e = np.minimum(up, down)
    return e * e * (3 - 2 * e)


def region_notes(series: np.ndarray, fps: float, t_in: float, t_out: float, struck: bool,
                 notes: list[int]) -> list[tuple[float, float, int, float]]:
    """(start s, length s, midi, velocity) on the beat grid while the pair is on screen."""
    beat = DAY_FRAMES / fps
    step = beat / STRUCK_SUBDIV if struck else beat * SUSTAIN_BEATS
    i0, i1 = int(t_in * fps), min(len(series), int(np.ceil(t_out * fps)))
    if i1 <= i0:
        return []
    slots = []                                            # (k, start, mean of the data over the note)
    k = int(np.ceil(t_in / step - 1e-9))
    while (t := k * step) < t_out and (a := int(t * fps)) < len(series):
        slots.append((k, t, float(series[a:max(a + 1, int((t + step) * fps))].mean())))
        k += 1
    if not slots:
        return []
    # Rank scale: each note's place among this voice's notes while the pair is on screen (0 = lowest,
    # 1 = highest), so one bright spike cannot squash the rest of the melody onto a single pitch.
    raw = np.array([s[2] for s in slots])
    ranks = (np.argsort(np.argsort(raw, kind="stable"), kind="stable") / max(len(raw) - 1, 1)
             if np.ptp(raw) > 1e-9 else np.full(len(raw), 0.5))
    out: list[tuple[float, float, int, float]] = []
    for (k, t, _), v in zip(slots, ranks):
        v = float(v)
        midi = notes[int(round(v * (len(notes) - 1)))]
        if struck:
            if v >= REST_BELOW or REST_BELOW <= 0:
                vel = (1.0 if k % STRUCK_SUBDIV == 0 else ACCENT) * (0.6 + 0.4 * v)
                out.append((t, step, midi, vel))
        elif out and out[-1][2] == midi and abs(out[-1][0] + out[-1][1] - t) < 1e-6:
            s, d, m, vel = out[-1]                       # same pitch again: hold it (legato)
            out[-1] = (s, d + step, m, vel)
        else:
            out.append((t, step, midi, 0.8 + 0.2 * v))
    return out


def render_region(name: str, f, ctx, env: np.ndarray) -> np.ndarray:
    r = REGIONS[name]
    spec = INSTRUMENTS[r["inst"]]
    t_in, t_out = PAIRS[r["pair"]]()
    series = sum(f.table[c] for c in r["cols"]).rolling(MELODY_SMOOTH_FRAMES, center=True, min_periods=1)
    pan = float(np.clip(r["pan"] * PAN_WIDTH, -1, 1))
    out = np.zeros((ctx.n_samples, 2))
    for t, dur, midi, vel in region_notes(series.mean().to_numpy(), ctx.timeline.fps, t_in, t_out,
                                          spec["struck"], scale_notes(r["low"])):
        y = instrument_tone(r["inst"], mapping.midi_to_hz(midi), dur, ctx.sr) * vel
        synth.add_at(out, synth.pan_stereo(y, pan), t, ctx.sr)
    return synth.normalize(out * env[:, None])


PAIRS = {1: lambda: (PAIR1_IN, PAIR1_OUT), 2: lambda: (PAIR2_IN, PAIR2_OUT), 3: lambda: (PAIR3_IN, PAIR3_OUT)}


def render_breath(f, ctx, duck: np.ndarray) -> np.ndarray:
    n, sr = ctx.n_samples, ctx.sr
    haze = f.resampled("haze", n) / (f.table.haze.max() or 1.0)
    level = np.clip(haze, 0, 1) ** LEVEL_EXP
    smooth = f.table.haze.rolling(BREATH_SMOOTH_FRAMES, center=True, min_periods=1).mean().to_numpy()
    slope = np.diff(smooth, prepend=smooth[0])
    slope = np.interp(np.linspace(0, len(slope) - 1, n), np.arange(len(slope)), slope)
    rising = 0.5 + 0.5 * np.clip(SLOPE_SENS * slope / (np.abs(slope).max() or 1.0), -1, 1)
    return breath_sound(level, rising, n, sr) * duck[:, None]


def breath_sound(level: np.ndarray, rising: np.ndarray, n: int, sr: int) -> np.ndarray:
    """The breath for given loudness (0..1) and inhale share (0 = exhale, 1 = inhale) curves, stereo."""
    inhale = synth.band_noise(n, *INHALE_BAND, sr, seed=91)
    exhale = synth.band_noise(n, *EXHALE_BAND, sr, seed=92)
    flow = synth.band_noise(n, *FLOW_BAND, sr, seed=93)
    breath = (INHALE_W * rising * inhale + (1 - rising) * exhale + FLOW_W * flow) * level
    return synth.normalize(synth.pan_stereo(breath, 0.0))


# ---- sound legend: one short clip per layer, for learning the sounds before the movie ----------------

def samples(sr: int = synth.SR) -> dict[str, tuple[str, np.ndarray]]:
    """name -> (spoken explanation, short stereo clip). Same sound models and pans as render()."""
    out = {}
    n = int(6.0 * sr)
    t = np.arange(n) / sr
    swell = np.sin(np.pi * t / t[-1])                         # haze grows, then fades
    out["breath"] = ("Breath: the tan haze. It gets louder and brighter while the haze grows, "
                     "then quieter and darker as it fades.",
                     breath_sound(swell ** LEVEL_EXP, (t < t[-1] / 2).astype(float), n, sr))

    heart = sonify.load(Path(__file__).with_name("co2_13_heartbeat_improved.py"))
    beat = DAY_FRAMES / 30.0
    clip = np.zeros((int(7 * beat * sr), 2))
    for i, s in enumerate([1.0, 1.0, 1.0, 0.0, 0.0, 0.0]):    # three strong beats, three faint ones
        level = heart.WEAKEST + (1 - heart.WEAKEST) * s ** 1.5
        for shape, gain, dt in ((heart.LUB, 1.0, 0.0), (heart.DUB, heart.DUB_LEVEL, 0.3)):
            body = heart.thump(sr=sr, **shape)
            warm = heart.thump(heart.WARM_PITCH * shape["f0"], heart.WARM_PITCH * shape["f1"],
                               shape["length"], shape["attack"], sr)
            synth.add_at(clip, synth.pan_stereo((body + heart.WARM_LEVEL * s ** 2 * warm) * gain * level, 0.0),
                         i * beat + dt, sr)
    out["heart"] = ("Heartbeat: one beat per model day. Strong when there is little CO2 colour on screen, "
                    "faint when there is a lot.", synth.normalize(clip))

    for name, r in REGIONS.items():                           # its scale up, low = less, high = more
        spec, scale = INSTRUMENTS[r["inst"]], scale_notes(r["low"])
        step = 0.4 if spec["struck"] else 0.7
        clip = np.zeros((int((len(scale) * step + 2.0) * sr), 2))
        pan = float(np.clip(r["pan"] * PAN_WIDTH, -1, 1))
        for i, midi in enumerate(scale):
            y = instrument_tone(r["inst"], mapping.midi_to_hz(midi), step, sr) * (0.6 + 0.4 * i / (len(scale) - 1))
            synth.add_at(clip, synth.pan_stereo(y, pan), i * step, sr)
        label = name.replace("_", " ").title()
        side = "on the left" if pan < -0.2 else "on the right" if pan > 0.2 else "in the centre"
        out[name] = (f"{label}: {r['inst']}, heard {side}. Low notes mean little orange-red CO2 in its "
                     f"part of the screen, high notes mean a lot.", synth.normalize(clip))
    return out


def render(ctx):
    f = ctx.frame_features()
    n, sr = ctx.n_samples, ctx.sr
    envs = {p: window(n, sr, *get()) for p, get in PAIRS.items()}
    activity = np.max(np.stack(list(envs.values())), axis=0)
    duck = 10 ** (-DUCK_DB * activity / 20)

    stems = {"breath": render_breath(f, ctx, duck),
             "heart": sonify.run(Path(__file__).with_name("co2_13_heartbeat_improved.py"), ctx)}
    for name, r in REGIONS.items():
        stems[name] = render_region(name, f, ctx, envs[r["pair"]])
    return stems
